FROM python:3.10
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
ENV PORT=7860
EXPOSE 7860
CMD ["python", "shiyuk_bot.py"]
