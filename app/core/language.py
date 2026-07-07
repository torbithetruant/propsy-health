from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

class LanguageMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Safely check if SessionMiddleware has run and populated the session
        if "session" in request.scope:
            lang = request.session.get("lang", "en")
        else:
            lang = "en"
        
        # Allow language switch via query parameter (e.g., ?lang=fr)
        if "lang" in request.query_params:
            new_lang = request.query_params["lang"]
            if new_lang in ["en", "fr"]:
                lang = new_lang
                # Save to session if it exists
                if "session" in request.scope:
                    request.session["lang"] = lang
        
        # Store language in request state so templates can access it
        request.state.lang = lang
        
        response = await call_next(request)
        return response