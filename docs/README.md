# Run local

## Backend

cd backend/

python -m venv venv

source venv/bin/activate

pip install --no-cache-dir -r requirements.txt

uvicorn app.main:app --reload


## Frontend

cd frontend

npm install

npm run dev

# Docker run

cd smart-contract-auditor

docker-compose up --build
