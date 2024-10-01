from django.shortcuts import render,redirect
import pyodbc
from uuid import uuid4
from django.views.decorators.http import require_http_methods
from datetime import datetime
from decimal import Decimal
from django.core.cache import cache


# Create your views here.
def obtain_data():
    server = '172.16.1.203'
    database = 'mrccentral'
    username = 'itahue2018'
    password = '1t4mrc2018'

    try:
        # Establecer la conexión con la base de datos
        conn = pyodbc.connect('DRIVER={SQL Server};SERVER=' + server + ';DATABASE=' + database + ';UID=' + username + ';PWD=' + password)
        conn.setdecoding(pyodbc.SQL_CHAR, encoding='latin1')
        conn.setencoding(encoding='latin1')
        cursor = conn.cursor()

        # Extraer año, mes y día de la fecha proporcionada
        year = datetime.now().year
        month = datetime.now().month
        day = 21
        # datetime.now().day

        # Consulta SQL dinámica basada en la fecha
        query = f"""
        SELECT L.nom_local, SUM(V.CantidadxPrecio) AS Total
        FROM MRC_VENTA_DETALLE_PERCAPITA AS V
        INNER JOIN locales AS L ON V.PuntoVenta = L.num_local
        WHERE YEAR(V.FechaVenta) = {year} AND MONTH(V.FechaVenta) = {month} AND DAY(V.FechaVenta) = {day}
        GROUP BY L.nom_local
        """

        cursor.execute(query)
        rows = cursor.fetchall()

        # Procesar los resultados
        data = []
        for row in rows:
            data.append({'local': row.nom_local, 'total': row.Total})

    except pyodbc.Error as e:
        print("Error en la conexión o consulta a la base de datos:", e)
        data = []

    return data


def obtain_raw_public():
    server = '172.20.8.5'
    database = 'HandshakeDB'
    username = 'sa'
    password = 'Skidata!'

    try:
        conn = pyodbc.connect('DRIVER={SQL Server};SERVER='+server+';DATABASE='+database+';UID='+username+';PWD='+password)
        conn.setdecoding(pyodbc.SQL_CHAR, encoding='latin1')
        conn.setencoding(encoding='latin1')
        cursor = conn.cursor()

        query = """
        SELECT Entries FROM Counters
        WHERE (Name = 'Fantasilandia') AND (ClientId = 1)
        """

        cursor.execute(query)
        row = cursor.fetchone()  # Obtiene solo la primera fila

        data = []
        if row:
            # row[0] es el primer valor (Entries) de la fila retornada
            data.append({'entries': row[0]})
        
    except pyodbc.Error as e:
        print("Error en la conexión o consulta a la base de datos:", e)
        data = []
        
    return data 








def signin(request):
    token_cookie = request.COOKIES.get('token-monitor')
    username_cookie = request.COOKIES.get('username-monitor')

    if token_cookie and username_cookie:
        if is_valid_token(token_cookie, username_cookie):
            return redirect('monitor')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Llama a la función login que autentica contra la base de datos
        user = login(username, password)

        if user is not None:
            token = str(uuid4())
            response = redirect('/monitor/')
            response.set_cookie('username-monitor', user['username'])
            response.set_cookie('token-monitor', token)
            
            # Set token in the database
            set_token(token, user['username'])

            return response
        else:
            error = 'Username or password is incorrect'
            # Vuelve a renderizar la plantilla de inicio de sesión con el mensaje de error
            return render(request, 'signin.html', {'error': error})

    # Si no es un POST, simplemente renderiza la página de inicio de sesión sin error
    return render(request, 'signin.html')


def monitor(request):
    token_cookie = request.COOKIES.get('token-monitor')
    username_cookie = request.COOKIES.get('username-monitor')
    is_authenticated = is_valid_token(token_cookie, username_cookie)

    # Intenta obtener los datos del caché, si no están, los consulta y los almacena por 15 minutos (900 segundos)
    datos_monitor = cache.get_or_set('datos_monitor', obtain_data, 900)
    publico_raw = cache.get_or_set('publico_raw', obtain_raw_public, 900)

    monitor_data = []
    if datos_monitor:
        for data in datos_monitor:
            # Convertir 'total' a Decimal directamente
            total_value = Decimal(data['total'])

            # Asegurarse de que publico_raw tiene datos y que no hay división por cero
            if publico_raw and publico_raw[0]['entries'] > 0:
                presupuesto = total_value / Decimal(publico_raw[0]['entries'])
            else:
                presupuesto = Decimal(0)

            # Formatear 'total' y 'presupuesto'
            monitor_data.append({
                'local': data['local'].strip(),
                'total': "{:,.0f}".format(total_value) if total_value == total_value.to_integral_value() else "{:,.2f}".format(total_value),
                'presupuesto': "{:,.2f}".format(presupuesto),  # Formatear el presupuesto con 2 decimales
            })

    context = {
        'username': username_cookie,
        'is_authenticated': is_authenticated,
        'monitor_data': monitor_data,
    }

    # Verifica que el token y el usuario sean válidos
    if token_cookie and username_cookie:
        if is_valid_token(token_cookie, username_cookie):
            return render(request, 'monitor.html', context)

    # Si no está autenticado, redirige a la página de inicio de sesión
    return redirect('signin')


def login(username, password):
    server = '172.20.8.252\\SQLEXPRESS'
    database = 'informatica'
    username_db = 'sa'
    password_db = 'Superman8'
    
    try:
        # Conectar a la base de datos
        conn = pyodbc.connect('DRIVER={SQL Server};SERVER='+server+';DATABASE='+database+';UID='+username_db+';PWD='+password_db)
        
        # Configurar codificación si es necesario
        conn.setdecoding(pyodbc.SQL_CHAR, encoding='latin1')
        conn.setencoding(encoding='latin1')
        
        cursor = conn.cursor()
        query = """
        SELECT UserID, Password FROM LVPS_User
        WHERE UserID = ?
        """
        
        cursor.execute(query, (username,))
        row = cursor.fetchone()
        
        if row and row.Password == password:
            return {'username': row.UserID}
        else:
            return None

    except pyodbc.Error as e:
        print("Error en la conexión o consulta a la base de datos:", e)
        return None



def is_valid_token(token, username):
    server = '172.20.8.252\\SQLEXPRESS'
    database = 'informatica'
    username_db = 'sa'
    password_db = 'Superman8'

    try:
        # Connect to the database
        conn = pyodbc.connect('DRIVER={SQL Server};SERVER='+server+';DATABASE='+database+';UID='+username_db+';PWD='+password_db)
        
        # Configure encoding if needed
        conn.setdecoding(pyodbc.SQL_CHAR, encoding='latin1')
        conn.setencoding(encoding='latin1')
        
        cursor = conn.cursor()
        query = """
        Select Token from LVPS_User
        WHERE UserID = ?
        """

        cursor.execute(query, (username,))
        row = cursor.fetchone()

        if row and row.Token == token:
            return True
        else:
            return False
    
    except Exception as e:
        print("Error occurred:", e)
        return False
    


def set_token(token, username):
    server = '172.20.8.252\\SQLEXPRESS'
    database = 'informatica'
    username_db = 'sa'
    password_db = 'Superman8'

    try:
        # Connect to the database
        conn = pyodbc.connect('DRIVER={SQL Server};SERVER='+server+';DATABASE='+database+';UID='+username_db+';PWD='+password_db)
        
        # Configure encoding if needed
        conn.setdecoding(pyodbc.SQL_CHAR, encoding='latin1')
        conn.setencoding(encoding='latin1')
        
        cursor = conn.cursor()
        query = """
        UPDATE LVPS_User
        SET Token = ?
        WHERE UserID = ?
        """
        
        # Execute the query with parameters
        cursor.execute(query, (token, username))
        conn.commit()

        
    except Exception as e:
        print("Error occurred:", e)
    
    finally:
        # Ensure resources are released
        cursor.close()
        conn.close()



@require_http_methods(["GET"])
def home(request):
    username = request.COOKIES.get('username-monitor')
    token = request.COOKIES.get('token-monitor')

    # Verifica si el token es válido
    is_authenticated = is_valid_token(token, username)


    context = {
        'username': username,
        'is_authenticated': is_authenticated
    }
    
    return render(request, 'base.html', context)

def signout(request):
    response = redirect('signin')
    response.delete_cookie('token-monitor')
    response.delete_cookie('username-monitor')
    return response