# 1. Python ka base image use karo
FROM python:3.9-slim

# 2. App directory set karo
WORKDIR /app

# 3. Zaroori system dependencies install karo
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/apt/lists/*

# 4. Apni files copy karo
COPY . .

# 5. Libraries install karo
RUN pip3 install -r requirements.txt

# 6. Port expose karo (Hugging Face hamesha 7860 use karta hai)
EXPOSE 7860

# 7. Streamlit ko chalne ki command do
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=7860", "--server.address=0.0.0.0"]
