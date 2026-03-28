from fastapi import FastAPI
app = FastAPI()

@app.get("/")
def test():
    return {"message": "choluj je zmrd"}

if __name__ == "__main__":
    main()
print("This is a test of the halovamake package.")
