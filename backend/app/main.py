from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.routes import router


app = FastAPI(title="C-Minus AI Tutor")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.get("/")
def root():
    return {"message": "C-Minus AI Tutor Backend is running"}