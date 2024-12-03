import os
import boto3
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import shutil

# Carga las variables de entorno del archivo .env
load_dotenv()

def login_to_databricks(driver, databricks_login_url, email):
    
    # Navega a la URL de login de Databricks
    print("\nNavegando a la URL de Databricks...\n")
    driver.get(databricks_login_url)
    
    time.sleep(2)

    # Rellena el campo de correo electrónico
    print("\nEsperando que se introduzca el correo electrónico...\n")
    wait = WebDriverWait(driver, 20)
    email_field = wait.until(EC.presence_of_element_located((By.NAME, 'email')))
    email_field.send_keys(email)
    email_field.send_keys(Keys.RETURN)
    
    # Espera a que se complete el inicio de sesión y se mande el código de verificación al correo electrónico
    time.sleep(10)

    # Solicita que al usuario que ingrese ese código de verificación
    verification_code = input("\nIntroduce el código de verificación enviado a tu correo (formato: XXX-XXX): ")

    # Introduce ese código de verificación en los campos de la página web de Databricks
    first_verification_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[aria-label^="Enter verification code character 1"]')))
    # Pega el código de verificación completo en la primera casilla
    first_verification_field.send_keys(verification_code.replace("-", ""))
    # Verifica que el código de verificación se haya ingresado correctamente
    verification_code_fields = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'input[aria-label^="Enter verification code character"]')))
    verification_code_parts = verification_code.replace("-", "")
    for i, field in enumerate(verification_code_fields):
        if field.get_attribute('value') != verification_code_parts[i]:
            raise Exception(f"El carácter en la posición {i+1} no coincide con el código de verificación ingresado.")
    # Mensaje de confirmación
    print("\nEl código de verificación se ha ingresado correctamente.\n")

    # Imprime el contenido de la página después de ingresar el código de verificación
    print(driver.page_source)

    # Espera a que se complete el inicio de sesión después de ingresar el código de verificación
    time.sleep(10)

    # Verifica si se ha iniciado sesión correctamente
    if "Sign in to Databricks Community Edition" in driver.page_source:
        raise Exception("El inicio de sesión no se completó correctamente. La página volvió a solicitar el correo electrónico.")

def download_file_from_databricks_with_selenium(databricks_login_url, databricks_download_url, email):
    
    # Configura el controlador de Chrome
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    prefs = {"download.default_directory": os.path.join(os.getcwd(), "downloads")}
    options.add_experimental_option("prefs", prefs)
    driver = webdriver.Chrome(options=options)

    downloaded_file = None  # Inicializa la variable antes del bloque try

    try:
        login_to_databricks(driver, databricks_login_url, email)

        # Descarga el archivo
        print("\nDescargando el archivo...\n")
        driver.get(databricks_download_url)
        time.sleep(10)  # Espera a que se descargue el archivo

        # Verifica que el archivo se haya descargado en la carpeta de descargas
        downloads_folder = os.path.join(os.getcwd(), "downloads")
        downloaded_file_path = os.path.join(downloads_folder, 'bajar_de_databricks.csv')
        if not os.path.exists(downloaded_file_path):
            raise Exception("No se encontró el archivo descargado en la carpeta de descargas")

        with open(downloaded_file_path, 'r', encoding='utf-8') as file:
            downloaded_file = file.read()

        if downloaded_file:
            print(f'\nArchivo descargado de {databricks_download_url} y almacenado en la variable\n')
        else:
            raise Exception("No se encontró el archivo descargado")

    except Exception as e:
        print(f'\nError descargando archivo: {e}\n')
        print(driver.page_source)  # Imprime el contenido de la página para ayudar a depurar
        print('\n')

    finally:
        driver.quit()
        
        return downloaded_file
    
def upload_file_to_bucket(bucket_name, file_content, file_name):
    s3_client = boto3.client('s3')

    try:
        # Subir el contenido del archivo al bucket de AWS S3
        s3_client.put_object(Bucket=bucket_name, Key=file_name, Body=file_content)
        print(f'\nEl contenido del archivo ha sido subido al bucket {bucket_name} como {file_name}\n')
    except Exception as e:
        print(f'\nError subiendo archivo: {e}\n')

def download_file_from_bucket(bucket_name, file_name, file_path):
    s3_client = boto3.client('s3')
    
    try:
        # Descargar el archivo del bucket de AWS S3
        s3_client.download_file(bucket_name, file_name, file_path)
        print(f'\n{file_name} ha sido descargado del bucket {bucket_name} y guardado como {file_path}\n')
    except Exception as e:
        print(f'\nError descargando archivo: {e}\n')

def upload_file_to_databricks_with_selenium(databricks_login_url, databricks_upload_url, email, file_path):
    
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(options=options)

    try:
        login_to_databricks(driver, databricks_login_url, email)

        # Navega a la URL de subida de archivo en Databricks
        print("\nNavegando a la URL de subida de archivo en Databricks...\n")
        driver.get(databricks_upload_url)
        time.sleep(5)  # Espera a que se cargue la página de subida

        # Encuentra el campo de subida de archivo y sube el archivo
        wait = WebDriverWait(driver, 20)
        upload_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="file"]')))
        upload_field.send_keys(file_path)

        # Espera a que se complete la subida del archivo
        time.sleep(10)
        print(f'\nEl archivo {file_path} ha sido subido a {databricks_upload_url}\n')

    except Exception as e:
        print(f'\nError subiendo archivo: {e}\n')
        print(driver.page_source)  # Imprime el contenido de la página para ayudar a depurar
        print('\n')

    finally:
        driver.quit()

if __name__ == "__main__":
    
    # Eliminar el contenido de la carpeta downloads si existe la carpeta
    downloads_folder = os.path.join(os.getcwd(), "downloads")
    if os.path.exists(downloads_folder):
        for filename in os.listdir(downloads_folder):
            file_path = os.path.join(downloads_folder, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f'Error al eliminar {file_path}. Razón: {e}')
    
    # URL para el login en Databricks
    databricks_login_url = "https://community.cloud.databricks.com/login.html?tuuid=bacfb74f-a879-44ab-b263-943e1587391e"
    
    # 1.- DESCARGAR ARCHIVO DESDE DATABRICKS Y CARGAR EN AWS S3
    
    # URL para descargar archivo desde Databricks
    databricks_download_url = 'https://community.cloud.databricks.com/files/tables/bajar_de_databricks.csv?o=2970632640926019'
    email = os.getenv('EMAIL')
    downloaded_file = download_file_from_databricks_with_selenium(databricks_login_url, databricks_download_url, email)
    
    # Imprimir el archivo descargado
    if downloaded_file:
        print(f'\nEl contenido del archivo descargado es:\n{downloaded_file}\n')
    else:
        print('\nNo se pudo descargar el archivo.\n')
        
    # Subir archivo a AWS S3
    bucket_name = "databricks-marcosparicio"
    if downloaded_file:
        file_name = 'subir_desde_vscode/bajar_de_databricks.csv'
        upload_file_to_bucket(bucket_name, downloaded_file, file_name)
        
    # 2.- DESCARGAR ARCHIVO DESDE AWS S3 Y CARGAR EN DATABRICKS
    
    # Descargar archivo desde AWS S3
    bucket_name = "databricks-marcosparicio"
    file_name = 'bajar_desde_vscode/subir_a_databricks.csv'
    file_path = 'downloads/subir_a_databricks.csv'
    download_file_from_bucket(bucket_name, file_name, file_path)
    
    # URL para cargar archivo en Databricks
    databricks_upload_url = 'https://community.cloud.databricks.com/tables/new/file?o=2970632640926019'
    email = os.getenv('EMAIL')
    file_path = os.path.abspath('downloads/subir_a_databricks.csv')
    upload_file_to_databricks_with_selenium(databricks_login_url, databricks_upload_url, email, file_path)