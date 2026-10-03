import requests

NODE_API_URL = "https://api.nx-store.com"


class NodeAPIError(Exception):
    pass


def node_request(request, method, endpoint, **kwargs):
    token = request.session.get("node_token")

    if not token:
        raise NodeAPIError("Tokenul Node.js lipsește din sesiunea Django.")

    headers = kwargs.pop("headers", {})

    headers["Authorization"] = f"Bearer {token}"
    headers["Accept"] = "application/json"

    try:
        response = requests.request(
            method=method,
            url=f"{NODE_API_URL}{endpoint}",
            headers=headers,
            timeout=15,
            **kwargs,
        )
    except requests.RequestException as error:
        raise NodeAPIError(
            f"Backend-ul Node.js nu poate fi accesat: {error}"
        )

    if response.status_code == 401:
        raise NodeAPIError(
            "Sesiunea Node.js este invalidă sau a expirat."
        )

    if response.status_code == 403:
        raise NodeAPIError(
            "Nu ai permisiunea necesară."
        )

    if not response.ok:
        raise NodeAPIError(
            f"Node API error {response.status_code}: {response.text}"
        )

    try:
        return response.json()
    except ValueError:
        raise NodeAPIError(
            "Backend-ul nu a returnat JSON valid."
        )