"""
API v1 Router.

Aggregates all v1 API endpoints.
"""

from fastapi import APIRouter
from backend.app.api.v1.endpoints import (
    auth, admin, hub_owner, parcel_owner, fleet_owner, 
    route_discovery, route_request_decision,
    trip_creation, trip_visibility,
    driver_assignment, driver_visibility,
    trip_execution, live_tracking
)

router = APIRouter()

# Include authentication endpoints
router.include_router(auth.router)

# Include admin endpoints
router.include_router(admin.router)

# Phase 2.1 - Hub Owner endpoints
router.include_router(hub_owner.router)

# Phase 2.2 - Parcel Owner endpoints
router.include_router(parcel_owner.router)

# Phase 2.3.1 - Fleet Owner endpoints
router.include_router(fleet_owner.router)

# Phase 2.3.2 - Route Discovery endpoints
router.include_router(route_discovery.router)

# Phase 2.3.3 - Route Request Decision endpoints
router.include_router(route_request_decision.router)

# Phase 2.4.1 - Trip Creation endpoints
router.include_router(trip_creation.router)
router.include_router(trip_visibility.router)

# Phase 2.4.2 - Driver Assignment endpoints
router.include_router(driver_assignment.router)
router.include_router(driver_visibility.router)

# Phase 2.5 - Live Trip Execution endpoints
router.include_router(trip_execution.router)
router.include_router(live_tracking.fleet_router)
router.include_router(live_tracking.hub_router)

# Phase 2.6 - Billing endpoints
from backend.app.api.v1.endpoints import admin_billing, owner_billing
router.include_router(admin_billing.router)
router.include_router(owner_billing.hub_router)
router.include_router(owner_billing.fleet_router)

# Phase 2.7 - Analytics endpoints
from backend.app.api.v1.endpoints import analytics
router.include_router(analytics.fleet_router)
router.include_router(analytics.hub_router)
router.include_router(analytics.admin_router)

# Phase 3 - Ops endpoints
from backend.app.api.v1.endpoints import admin_ops
router.include_router(admin_ops.router)

# Phase 0.5 - Notifications (Hotfix)
from backend.app.api.v1.endpoints import notifications
router.include_router(notifications.router)
router.include_router(notifications.admin_router)

# Future domain API routes will be added here
# Example:
# from backend.app.api.v1.endpoints import fleet, hubs, trips
# router.include_router(fleet.router, prefix="/fleet", tags=["Fleet"])
# router.include_router(hubs.router, prefix="/hubs", tags=["Hubs"])
