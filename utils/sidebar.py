import math
import inspect
import os
import streamlit as st
from typing import Dict, List, Optional


def price_area_sidebar(
    price_areas: List[str],
    area_coords: Optional[Dict[str, Dict]] = None,
    key: str = "selected_area",
    default: Optional[str] = None,
    show_city: bool = True,
    groups: Optional[List[str]] = None,
    group_key: str = "selected_group",
) -> str:
    """
    Render a global price-area selector in the sidebar and store selection in session_state.
    - price_areas: list of area ids (e.g. ['NO1','NO2',...'])
    - area_coords: optional mapping to resolve city/name for display
    - key: session_state key to store the selection (default 'selected_area')
    - default: fallback area id if none set
    Returns the selected area id (and ensures st.session_state[key] is set).
    """
    if not price_areas:
        raise ValueError("price_areas must be a non-empty list")

    # Fallback coords mapping for NO1-NO5 if not provided
    DEFAULT_AREA_COORDS = {
        'NO1': {'latitude': 59.91, 'longitude': 10.75, 'name': 'Oslo'},
        'NO2': {'latitude': 60.39, 'longitude': 5.32,  'name': 'Bergen'},
        'NO3': {'latitude': 63.43, 'longitude': 10.39, 'name': 'Trondheim'},
        'NO4': {'latitude': 69.65, 'longitude': 18.96, 'name': 'Tromsø'},
        'NO5': {'latitude': 58.1467, 'longitude': 7.9956, 'name': 'Kristiansand'}
    }
    if area_coords is None:
        area_coords = DEFAULT_AREA_COORDS

    # Initialize session state if missing
    if key not in st.session_state:
        st.session_state[key] = default if default in price_areas else price_areas[0]

    # Ensure coordinates exist for the initial selection
    initial = st.session_state.get(key)
    if initial in area_coords and 'selected_coordinates' not in st.session_state:
        ac = area_coords[initial]
        st.session_state['selected_coordinates'] = [ac['latitude'], ac['longitude']]
        st.session_state['selected_city'] = ac.get('name')

    # Determine currently selected index safely
    try:
        current_idx = price_areas.index(st.session_state.get(key))
    except ValueError:
        current_idx = 0
        st.session_state[key] = price_areas[0]

    # Determine a page-unique widget key based on the calling module filename and line number
    try:
        # find the first caller frame that's outside this utils file
        caller = None
        caller_lineno = None
        for fr in inspect.stack()[1:12]:
            fname = fr.filename or ''
            if os.path.abspath(fname) != os.path.abspath(__file__):
                caller = fname
                caller_lineno = getattr(fr, 'lineno', None)
                break
        page_suffix = os.path.splitext(os.path.basename(caller or 'app'))[0]
        line_suffix = f"_{caller_lineno}" if caller_lineno is not None else ''
    except Exception:
        page_suffix = 'app'
        line_suffix = ''

    widget_key = f"{key}_widget_{page_suffix}{line_suffix}"

    # Render selector in sidebar
    prev_selected = st.session_state.get(key)
    selected = st.sidebar.selectbox(
        "Price Area",
        options=price_areas,
        index=current_idx,
        key=widget_key,
    )

    # Persist selection to main session_state key
    st.session_state[key] = selected

    # If the selected area changed, invalidate cached area-specific data so pages will refresh
    if prev_selected != selected:
        # Remove cached weather data so it can be reloaded for the new area
        if 'weather_data' in st.session_state:
            del st.session_state['weather_data']
        if 'weather_area' in st.session_state:
            del st.session_state['weather_area']

    # Also update derived session values (coordinates, city) when available
    if area_coords and isinstance(area_coords, dict):
        coords = area_coords.get(selected)
        if coords:
            # Use latitude, longitude naming consistent with other pages
            lat = coords.get('latitude')
            lon = coords.get('longitude')
            if lat is not None and lon is not None:
                st.session_state['selected_coordinates'] = [lat, lon]
            if coords.get('name'):
                st.session_state['selected_city'] = coords.get('name')

    # Optionally render a production/consumption group selector in the sidebar
    if groups:
        # initialize group session key if missing
        if group_key not in st.session_state:
            st.session_state[group_key] = 'All groups'
        # determine current index
        # include an "All groups" option at the top
        groups_with_all = ["All groups"] + groups
        try:
            g_idx = groups_with_all.index(st.session_state.get(group_key))
        except Exception:
            g_idx = 0
            st.session_state[group_key] = 'All groups'

        group_widget_key = f"{group_key}_widget_{page_suffix}{line_suffix}"
        prev_group = st.session_state.get(group_key)
        selected_group = st.sidebar.selectbox("Group", options=groups_with_all, index=g_idx, key=group_widget_key)
        st.session_state[group_key] = selected_group
        # Optionally invalidate caches on group change (pages will recompute choropleth)
        if prev_group != selected_group:
            # Clear caches that depend on the selected group so pages recompute immediately.
            # weather_data is usually independent of group, but some derived computations
            # (choropleth values, aggregated dfs) may be stored in session_state under
            # a project-specific key. Remove common candidate keys if present.
            for k in ['choropleth_df', 'df_vals', 'choropleth_values', 'geojson_data', 'computed_group_aggregates']:
                if k in st.session_state:
                    st.session_state.pop(k, None)
            # Trigger a rerun so that all pages pick up the new group immediately.
            try:
                st.experimental_rerun()
            except Exception:
                # In some contexts (tests) rerun may not be available; ignore safely.
                pass

    return selected


def get_selected_area(key: str = "selected_area") -> Optional[str]:
    """Convenience getter for the currently selected price area."""
    return st.session_state.get(key)


def select_area_by_coordinates(lat: float, lon: float, price_areas: Optional[List[str]] = None, area_coords: Optional[Dict[str, Dict]] = None, key: str = "selected_area") -> Optional[str]:
    """
    Choose the nearest price area by haversine distance to the supplied lat/lon and update session_state.
    Returns the selected area id or None if no areas available.
    """
    # Use default coords if not provided
    DEFAULT_AREA_COORDS = {
        'NO1': {'latitude': 59.91, 'longitude': 10.75, 'name': 'Oslo'},
        'NO2': {'latitude': 60.39, 'longitude': 5.32,  'name': 'Bergen'},
        'NO3': {'latitude': 63.43, 'longitude': 10.39, 'name': 'Trondheim'},
        'NO4': {'latitude': 69.65, 'longitude': 18.96, 'name': 'Tromsø'},
        'NO5': {'latitude': 58.1467, 'longitude': 7.9956, 'name': 'Kristiansand'}
    }
    if area_coords is None:
        area_coords = DEFAULT_AREA_COORDS

    if price_areas is None:
        price_areas = list(area_coords.keys())

    def haversine(lat1, lon1, lat2, lon2):
        # return distance in kilometers
        R = 6371.0
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
        return 2 * R * math.asin(math.sqrt(a))

    best = None
    best_dist = float('inf')
    for pa in price_areas:
        c = area_coords.get(pa)
        if not c:
            continue
        d = haversine(lat, lon, c.get('latitude'), c.get('longitude'))
        if d < best_dist:
            best_dist = d
            best = pa

    if best:
        # update canonical session key
        st.session_state[key] = best
        # also try to update the widget key for the caller page (if present)
        try:
            # derive the same page-specific widget key as in price_area_sidebar
            caller = None
            for fr in inspect.stack()[1:5]:
                fname = fr.filename or ''
                if os.path.abspath(fname) != os.path.abspath(__file__):
                    caller = fname
                    break
            page_suffix = os.path.splitext(os.path.basename(caller or 'app'))[0]
            widget_key = f"{key}_widget_{page_suffix}"
            st.session_state[widget_key] = best
        except Exception:
            # widget may not exist; that's fine
            pass
        st.session_state['selected_coordinates'] = [lat, lon]
        if area_coords.get(best) and area_coords.get(best).get('name'):
            st.session_state['selected_city'] = area_coords.get(best).get('name')
        # Invalidate cached area-specific weather data so pages will refresh
        if 'weather_data' in st.session_state:
            del st.session_state['weather_data']
        if 'weather_area' in st.session_state:
            del st.session_state['weather_area']
    return best
