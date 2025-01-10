import numpy
import pdfminer
import os
from cx_Freeze import setup, Executable

# Definir opções de build
numpy_path = os.path.join(os.path.dirname(numpy.__file__), "core")
pdfminer_path = os.path.dirname(pdfminer.__file__)

build_exe_options = {
    "packages": [
        "os", "flask", "pdfminer", "pandas", "tempfile", "shutil", "unidecode", "difflib", "decimal", "re"
    ],
    "include_files": [
        ("resources/templates", "resources/templates"),  # Inclua templates
        ("resources/static", "resources/static"),         # Inclua arquivos estáticos, se existirem
        (pdfminer_path, "pdfminer"),                      # Inclua o diretório do pdfminer manualmente
        (numpy_path, "numpy/core")                        # Inclua o diretório do NumPy manualmente
    ],
    "excludes": ["tkinter", "PyQt5", "scipy", "numba", "sqlalchemy", "matplotlib"]  # Exclua bibliotecas desnecessárias para reduzir o tamanho
}

# Configurar executáveis
executables = [
    Executable(
        script="app.py",                  # Código principal do aplicativo
        base=None,  			# Habilita o console para depuração
        target_name="keypdfwin.exe"      # Nome do executável gerado
    )
]

# Configuração do setup
setup(
    name="keypdfwin",
    version="1.0",
    description="Aplicativo de Correspondência de PDFs",
    options={"build_exe": build_exe_options},
    executables=executables
)
