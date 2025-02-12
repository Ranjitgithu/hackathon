from flask import Flask, request, jsonify, render_template
import fitz  
import pytesseract
from PIL import Image
import io
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import TfidfVectorizer
import difflib
from werkzeug.utils import secure_filename
import os
import bcrypt
import pandas as pd 
import tempfile
from bs4 import BeautifulSoup
import requests
import nltk

# Download stopwords
nltk.download('stopwords')

app = Flask(__name__, template_folder='templates')

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def extract_text_from_image(image_file):
    try:
        image = Image.open(image_file)
        text = pytesseract.image_to_string(image)
        return text
    except Exception as e:
        return str(e)

def extract_text_from_pdf(pdf_file):
    pdf_document = fitz.open(stream=pdf_file.read(), filetype="pdf")
    text = ""
    for page_num in range(len(pdf_document)):
        page = pdf_document.load_page(page_num)
        page_text = page.get_text("text")
        if page_text.strip():
            text += page_text + "\n"
        else:
            pix = page.get_pixmap()
            img = Image.open(io.BytesIO(pix.tobytes()))
            page_text = pytesseract.image_to_string(img)
            text += page_text + "\n"
    return text.strip()

def extract_text_from_html(html_file):
    try:
        soup = BeautifulSoup(html_file, 'html.parser')
        text = soup.get_text()
        return text.strip()
    except Exception as e:
        return str(e)

def fetch_online_answer(question):
    search_url = f"https://www.google.com/search?q={question}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(search_url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    answer_element = soup.find('span', class_='BNeawe')
    if answer_element:
        return answer_element.text
    else:
        return "Answer not found"

def evaluate_answers(key_text, answer_text, weightages):
    key_lines = key_text.splitlines()
    answer_lines = answer_text.splitlines()
    total_marks = sum(weightages)
    obtained_marks = 0
    stop_words = stopwords.words('english')
    vectorizer = TfidfVectorizer(stop_words=stop_words)

    for (key, answer, weightage) in zip(key_lines, answer_lines, weightages):
        if not key.strip() or not answer.strip():
            continue  # Skip empty lines
        
        # Check for stop words only
        key_words = [word for word in key.split() if word.lower() not in stop_words]
        answer_words = [word for word in answer.split() if word.lower() not in stop_words]

        if not key_words or not answer_words:
            continue  # Skip lines that only contain stop words

        try:
            vectors = vectorizer.fit_transform([key, answer]).toarray()
            similarity = difflib.SequenceMatcher(None, vectors[0], vectors[1]).ratio()
            if similarity > 0.7:
                obtained_marks += weightage
            else:
                online_answer = fetch_online_answer(answer)
                if answer == online_answer:
                    obtained_marks += weightage
        except ValueError as e:
            print(f"Error processing line: {e}")
            continue
    
    score = (obtained_marks / total_marks) * 100 if total_marks else 0
    return score, obtained_marks

users = {
    "admin": bcrypt.hashpw("password123".encode('utf-8'), bcrypt.gensalt())
}

@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    password = request.form['password']
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    users[username] = hashed_password
    return jsonify({"message": "User registered successfully"})

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password'].encode('utf-8')
    hashed_password = users.get(username)
    if hashed_password and bcrypt.checkpw(password, hashed_password):
        return jsonify({"message": "Login successful"})
    else:
        return jsonify({"message": "Invalid credentials"})

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    student_id = request.form['student_id']
    user_id = request.form['user_id']
    password = request.form['password'].encode('utf-8')
    passkey = request.form.get('passkey')

    if user_id != 'admin' or not bcrypt.checkpw(password, users['admin']):
        return jsonify({"message": "Invalid user ID or password"}), 401

    if passkey != '123456':
        return jsonify({"message": "Invalid passkey"}), 403

    question_pdf = request.files.get('question_pdf')
    question_image = request.files.get('question_image')
    question_html = request.files.get('question_html')
    key_sheet_pdf = request.files.get('key_sheet_pdf')
    key_sheet_image = request.files.get('key_sheet_image')
    answer_sheet_pdf = request.files.get('answer_sheet_pdf')
    answer_sheet_image = request.files.get('answer_sheet_image')

    weightages = list(map(int, request.form.getlist('weightage')))

    if question_pdf:
        question_pdf.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(question_pdf.filename)))
    if question_image:
        question_image.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(question_image.filename)))
    if question_html:
        question_html.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(question_html.filename)))
    if key_sheet_pdf:
        key_sheet_pdf.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(key_sheet_pdf.filename)))
    if key_sheet_image:
        key_sheet_image.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(key_sheet_image.filename)))
    if answer_sheet_pdf:
        answer_sheet_pdf.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(answer_sheet_pdf.filename)))
    if answer_sheet_image:
        answer_sheet_image.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(answer_sheet_image.filename)))

    if question_pdf:
        question_pdf.seek(0)
    if question_image:
        question_image.seek(0)
    if question_html:
        question_html.seek(0)
    if key_sheet_pdf:
        key_sheet_pdf.seek(0)
    if key_sheet_image:
        key_sheet_image.seek(0)
    if answer_sheet_pdf:
        answer_sheet_pdf.seek(0)
    if answer_sheet_image:
        answer_sheet_image.seek(0)

    question_text = ""
    if question_pdf:
        question_text = extract_text_from_pdf(question_pdf)
    elif question_image:
        question_text = extract_text_from_image(question_image)
    elif question_html:
        question_text = extract_text_from_html(question_html)
    
    key_text = ""
    if key_sheet_pdf:
        key_text = extract_text_from_pdf(key_sheet_pdf)
    elif key_sheet_image:
        key_text = extract_text_from_image(key_sheet_image)
    
    answer_text = ""
    if answer_sheet_pdf:
        answer_text = extract_text_from_pdf(answer_sheet_pdf)
    elif answer_sheet_image:
        answer_text = extract_text_from_image(answer_sheet_image)
    
    score, obtained_marks = evaluate_answers(key_text, answer_text, weightages)

    with tempfile.TemporaryDirectory() as tempdir:
        temp_excel_file = os.path.join(tempdir, 'student_scores.xlsx')
        data = {'Student ID': [student_id], 'Accuracy Score': [score], 'Obtained Marks': [obtained_marks]}
        if os.path.exists(temp_excel_file):
            df = pd.read_excel(temp_excel_file)
            df = df.append(pd.DataFrame(data), ignore_index=True)
        else:
            df = pd.DataFrame(data)
        df.to_excel(temp_excel_file, index=False)
        os.replace(temp_excel_file, r'C:\Users\phani\OneDrive\Desktop\project\student_scores.xlsx')

    return jsonify({
        "student_id": student_id,
        "question_text": question_text,
        "key_text": key_text,
        "answer_text": answer_text,
        "evaluation_score": score,
        "obtained_marks": obtained_marks
    })

if __name__ == '__main__':
    app.run(debug=True)
