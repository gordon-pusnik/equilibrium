# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the poker-core sources
COPY poker-core/c++ /app/poker-core/c++

COPY ml/modeljob85.json /app/ml/modeljob85.json
COPY ml/modeljob96.json /app/ml/modeljob96.json

# Build the shared library
RUN g++ -std=c++17 -O3 -fPIC -shared \
    /app/poker-core/c++/card.cpp \
    /app/poker-core/c++/deck.cpp \
    /app/poker-core/c++/hand.cpp \
    /app/poker-core/c++/checkforwin.cpp \
    /app/poker-core/c++/autohold.cpp \
    /app/poker-core/c++/game_variant.cpp \
    /app/poker-core/c++/trainer_api.cpp \
    /app/poker-core/c++/evaluator.cpp \
    -o /app/libvideopoker.so

# Copy the API server code
COPY api-server/main.py /app/
COPY api-server/app /app/app
COPY api-server/requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port the app runs on
EXPOSE 8001

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
