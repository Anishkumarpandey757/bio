# OLS Balance Scorer Setup

## Create Virtual Environment and Install Dependencies

### Option 1: Using Python venv (Recommended)
```bash
# Navigate to your project directory
cd "c:\Users\anish\OneDrive\Desktop\bio med\ols_left_leg_eo"

# Create virtual environment
python -m venv ols_env

# Activate virtual environment
# On Windows:
ols_env\Scripts\activate

# Install requirements
pip install -r requirements.txt

# Run the application
streamlit run streamlit_ols_scorer.py
```

### Option 2: Using conda
```bash
# Create conda environment
conda create -n ols_env python=3.10

# Activate environment
conda activate ols_env

# Install requirements
pip install -r requirements.txt

# Run the application
streamlit run streamlit_ols_scorer.py
```

## Package Versions
- streamlit>=1.28.0
- opencv-python>=4.8.0
- numpy>=1.24.0
- pandas>=2.0.0
- mediapipe>=0.10.14
- protobuf<5

## Running the App
After installation, you can run the app with:
```bash
streamlit run streamlit_ols_scorer.py
```

The app will open in your browser at http://localhost:8501

## Usage
1. Upload Front view video (for SS parameters)
2. Upload Side view video (for AP parameters)  
3. Enter student information (optional)
4. Click "Process Videos & Calculate Scores"
5. View results and download CSV