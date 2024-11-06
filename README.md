## Установка и настройка
1. **Клонирование репозитория**

   Создайте папку для проекта и откройте консоль. Перейдите в папку.
   
   ```bash
   cd <название папки>
   ```
   Сначала клонируйте репозиторий или скачайте код в свою рабочую папку:

   ```bash
   git clone <URL репозитория>
   cd <название папки>
   ```
   Если скачивали файлы, то сначала распакуйте архив, затем откройте консоль и перейдите в рабочую папку:

   ```bash
   Копировать код
   cd <название папки>
   ```
## Создание и активация виртуального окружения

Перейдите в папку проекта, затем создайте виртуальное окружение в этой папке.

### Для Windows:
   ```bash
   python -m venv venv  # или py вместо python
   .\venv\Scripts\activate
   ```
### Для Linux/MacOS:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
## Установка зависимостей

После активации виртуального окружения установите все необходимые зависимости с помощью файла requirements.txt:

```bash
Копировать код
pip install -r requirements.txt
```
## Создание файла .env

В корневой папке проекта создайте файл .env для хранения конфиденциальной информации, такой как параметры подключения к Neo4j и токен доступа API.

Откройте файл .env и добавьте следующие строки, заменив на реальные значения:

```env
DATABASE_URL=bolt://user:password@localhost:7687
API_TOKEN=<токен доступа>
```
## Настройка подключения к Neo4j
Убедитесь, что сервер Neo4j запущен, и что данные подключения корректны. Программа автоматически считывает данные из файла .env. (dmp базы есть в репозитории)

# Тесты на каждую точку доступа и модель данных
## Описание тестов для API
Каждая точка доступа API протестирована на корректность обработки запросов и структуры ответов. В тестах проверяются:

- Статус-коды ответа (например, 200 для успешных операций, 400 для ошибок в запросах).
- Корректность структуры JSON-ответа, включая наличие обязательных полей и их значения.
### Примеры тестов для точек доступа
1. Тесты для каждого метода (GET, POST, PATCH, DELETE) обеспечивают проверку всех операций CRUD для пользователей и групп.

    Пример теста создания пользователя:
    ```python
    def test_create_user():
        user_data = {
            "user_id": 1,
            "name": "Test User",
            "subscriptions": []
        }
        response = client.post("/users/", json=user_data, headers={"token": API_TOKEN})
        assert response.status_code == 200
        assert response.json()["message"] == "User 1 created with name Test User"
     ```
2. Тесты для моделей данных. Модели данных также тестируются на создание экземпляров и на корректность их полей:

- Проверка создания экземпляров User и Group с обязательными полями.
- Проверка уникальности значений для user_id и group_id.
- Проверка отношений между моделями, таких как Follow и Subscribe.

  Пример теста для модели пользователя:
    ```python
    def test_user_creation():
    	user1 = User(user_id=1, name="User1", sex=1, home_town="Hometown1", city="City1").save()
    	assert user1.user_id == 1
    	assert user1.name == "User1"
    	assert user1.sex == 1
    	assert user1.home_town == "Hometown1"
    	assert user1.city == "City1"
     ```
# Универсальная инструкция для развертывания приложения на любом VDS-сервере

1. Подключитесь к серверу с помощью SSH:

```bash
ssh your_user@your_server_ip
```
2. Обновите систему и установите Python с pip, если он еще не установлен:

```bash
sudo apt update
sudo apt install python3 python3-pip -y
```
3. Создайте и активируйте виртуальное окружение для изоляции проекта:

```bash
python3 -m venv venv
source venv/bin/activate
```
4. Скопируйте файлы проекта на сервер и установите зависимости:

```bash
scp -r /path/to/your/project your_user@your_server_ip:/path/on/server
````
Затем на сервере перейдите в папку проекта и установите зависимости:

```bash
cd /path/on/server
pip install -r requirements.txt
```
5. Установите и настройте базу данных Neo4j. Для Ubuntu команды будут следующими:

```bash
wget -O - https://debian.neo4j.com/neotechnology.gpg.key | sudo apt-key add -
echo "deb https://debian.neo4j.com stable 4.3" | sudo tee /etc/apt/sources.list.d/neo4j.list
sudo apt update
sudo apt install neo4j -y
```
Запустите Neo4j и настройте пользователя и пароль. Убедитесь, что порт 7687 открыт:

```bash
sudo neo4j start
```
6. Создайте .env файл с переменными окружения, например:

```env
DATABASE_URL=bolt://<user>:<password>@localhost:7687
API_TOKEN=your_secret_token
```
7. Для запуска приложения выполните команду:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```
- main — это файл с вашим приложением FastAPI.
- app — это экземпляр FastAPI в этом файле.

8. Чтобы приложение работало постоянно, создайте службу с помощью systemd:

Создайте новый файл службы:
```bash
sudo nano /etc/systemd/system/fastapi-app.service
```
Добавьте в файл следующее содержимое:
```ini
[Unit]
Description=FastAPI Application
After=network.target

[Service]
User=your_user
WorkingDirectory=/path/to/your/project
ExecStart=/path/to/your/project/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```
Запустите и включите службу:
```bash
sudo systemctl start fastapi-app
sudo systemctl enable fastapi-app
```
Теперь ваше приложение будет запускаться автоматически после перезагрузки сервера.

9. Запустите тесты с помощью pytest, указав директорию с тестами:

```bash
pytest tests/
```