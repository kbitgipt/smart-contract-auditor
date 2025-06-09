# System support smart contract auditing with AI integration
## Run local

### Backend

```
cd backend/

python -m venv venv 

source venv/bin/activate

pip install --no-cache-dir -r requirements.txt

uvicorn app.main:app --reload --port 9000
```

### Frontend

```
cd frontend

npm install

npm run dev

# Docker run
```

## Docker

```
cd smart-contract-auditor
chmod +x run-docker.sh
./run-docker.sh

or docker-compose up --build

# clean up
chmod +x clean-docker.sh
./clean-docker.sh
```