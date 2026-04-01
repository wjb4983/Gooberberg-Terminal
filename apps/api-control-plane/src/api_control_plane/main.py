"""Entry module for api_control_plane."""

from fastapi import FastAPI

app = FastAPI(title="Gooberberg API Control Plane")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    """Return liveness state for local development."""
    return {"status": "ok"}


def main() -> None:
    """Run the api_control_plane placeholder entrypoint."""
    print("api_control_plane service skeleton")


if __name__ == "__main__":
    main()
