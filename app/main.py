from fastapi import FastAPI
from fastapi.routing import APIRoute
from collections import defaultdict
from app.api.routes.api import router as api_router

app = FastAPI(title="BE Tool API", description="Backend Tool API for internal management")
app.include_router(api_router, prefix="/api")

@app.get("/", summary="Danh sách API theo module")
async def root():
    grouped_routes = defaultdict(list)

    for route in app.routes:
        if isinstance(route, APIRoute) and not route.path.startswith(("/openapi", "/docs", "/redoc")):
            methods = [method for method in route.methods if method not in ("HEAD", "OPTIONS")]

            # Lấy module chính: ví dụ /api/users/1 => /api/users
            parts = route.path.strip("/").split("/")
            if len(parts) >= 2:
                group = f"/{parts[0]}/{parts[1]}"
            elif len(parts) == 1:
                group = f"/{parts[0]}"
            else:
                group = "/"

            grouped_routes[group].append({
                "path": route.path,
                "methods": methods,
                "summary": route.summary or "Không có mô tả"
            })

    # Sắp xếp từng group theo path
    grouped_routes = {k: sorted(v, key=lambda x: x["path"]) for k, v in grouped_routes.items()}

    return {"total_groups": len(grouped_routes), "grouped_routes": grouped_routes}
