def main():
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        import uvicorn

        uvicorn.run("api.main:app", host="127.0.0.1", port=8000, reload=True)
        return
    print("Hello from pythongine!")
    print("Run analysis API: uv run python main.py serve")


if __name__ == "__main__":
    main()
