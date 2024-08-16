run:
	poetry run streamlit run main.py

lint:
	poetry run black . && poetry run isort --profile=black .
