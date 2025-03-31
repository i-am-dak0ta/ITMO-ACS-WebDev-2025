# Практика 1.2. Настройка БД, SQLModel и миграции через Alembic

В рамках практики я настроил приложение на FastAPI с использованием SQLModel для работы с PostgreSQL. Реализовал модели для воинов, профессий, умений и их связей, а также CRUD-операции. Настроено вложенное отображение профессий и умений при запросе воина. Все эндпоинты протестированы через документацию по адресу `127.0.0.1:8000/docs`.

## Практическая часть

### Подключение к базе данных

В файле `connection.py` настроено подключение к PostgreSQL:

```python
from sqlmodel import SQLModel, Session, create_engine  
  
db_url = "postgresql://postgres:123123@localhost/warriors_db"  
engine = create_engine(db_url, echo=True)  
  
  
def init_db():  
    SQLModel.metadata.create_all(engine)  
  
  
def get_session():  
    with Session(engine) as session:  
        yield session
```

Инициализация таблиц вызывается в `main.py` при старте приложения:

```python
@app.on_event("startup")  
def on_startup():  
    init_db()
```

### Модели SQLModel

В файле `models.py` определены модели с учётом связей:

- **Воин и ответ с вложенными данными:**
```python
class WarriorDefault(SQLModel):  
    race: RaceType  
    name: str  
    level: int  
    profession_id: Optional[int] = Field(default=None, foreign_key="profession.id")  
  
  
class Warrior(WarriorDefault, table=True):  
    id: int = Field(default=None, primary_key=True)  
    profession: Optional[Profession] = Relationship(  
        back_populates="warriors_prof",  
        sa_relationship_kwargs={"lazy": "joined"},  
    )  
  
    skills: Optional[List[Skill]] = Relationship(  
        back_populates="warriors",  
        link_model=SkillWarriorLink,  
        sa_relationship_kwargs={"uselist": True, "lazy": "selectin"},  
    )

class WarriorProfessions(WarriorDefault):  
    profession: Optional[Profession] = None  
  
  
class WarriorResponse(WarriorProfessions):  
    id: int  
    skills: List[Skill]
```

- **Профессия:**
```python
class ProfessionDefault(SQLModel):  
    title: str  
    description: str  

class Profession(ProfessionDefault, table=True):  
    id: int = Field(default=None, primary_key=True)  
    warriors_prof: List["Warrior"] = Relationship(back_populates="profession")
```

- **Умение и ассоциативная таблица:**
```python
class SkillWarriorLink(SQLModel, table=True):  
    skill_id: Optional[int] = Field(  
        default=None, foreign_key="skill.id", primary_key=True  
    )  
    warrior_id: Optional[int] = Field(  
        default=None, foreign_key="warrior.id", primary_key=True  
    )  
  
  
class SkillDefault(SQLModel):  
    name: str  
    description: Optional[str] = ""  
  
  
class Skill(SkillDefault, table=True):  
    id: int = Field(default=None, primary_key=True)  
    warriors: Optional[List["Warrior"]] = Relationship(  
        back_populates="skills",  
        link_model=SkillWarriorLink  
    )
```

### Эндпоинты для воинов

Реализованы CRUD-операции в `main.py`:

- **Создание воина:**
```python
@app.post("/warrior")  
def warriors_create(warrior: WarriorDefault, session=Depends(get_session)):  
    warrior = Warrior.model_validate(warrior)  
    session.add(warrior)  
    session.commit()  
    session.refresh(warrior)  
    return {"status": 200, "data": warrior}
```

- **Получение списка воинов:**
```python
@app.get("/warriors_list")  
def warriors_list(session=Depends(get_session)) -> List[Warrior]:  
    return session.exec(select(Warrior)).all()
```

- **Получение воина с профессией и умениями:**
```python
@app.get("/warrior/{warrior_id}", response_model=WarriorResponse)  
def warriors_get(warrior_id: int, session=Depends(get_session)) -> Warrior:  
    warrior = session.get(Warrior, warrior_id)  
    return warrior
```

- **Обновление воина:**
```python
@app.patch("/warrior/{warrior_id}")  
def warrior_update(  
        warrior_id: int, warrior: WarriorDefault, session=Depends(get_session)  
) -> WarriorDefault:  
    db_warrior = session.get(Warrior, warrior_id)  
    if not db_warrior:  
        raise HTTPException(status_code=404, detail="Warrior not found")  
  
    warrior_data = warrior.model_dump(exclude_unset=True)  
    for key, value in warrior_data.items():  
        setattr(db_warrior, key, value)  
  
    session.add(db_warrior)  
    session.commit()  
    session.refresh(db_warrior)  
    return db_warrior
```

- **Удаление воина:**
```python
@app.delete("/warrior/{warrior_id}")  
def warrior_delete(warrior_id: int, session=Depends(get_session)):  
    warrior = session.get(Warrior, warrior_id)  
    if not warrior:  
        raise HTTPException(status_code=404, detail="Warrior not found")  
    session.delete(warrior)  
    session.commit()  
    return {"ok": True}
```

### Эндпоинты для профессий

- **Получение списка профессий:**
```python
@app.get("/professions_list")  
def professions_list(session=Depends(get_session)) -> List[Profession]:  
    return session.exec(select(Profession)).all()
```

- **Получение конкретной профессии:**
```python
@app.get("/profession/{profession_id}")  
def profession_get(profession_id: int, session=Depends(get_session)) -> Profession:  
    return session.get(Profession, profession_id)
```

- **Создание профессии:**
```python
@app.post("/profession")  
def profession_create(prof: ProfessionDefault, session=Depends(get_session)):  
    prof = Profession.model_validate(prof)  
    session.add(prof)  
    session.commit()  
    session.refresh(prof)  
    return {"status": 200, "data": prof}
```

### Эндпоинты для умений

Добавлены операции для управления умениями и их привязкой к воинам:

- **Добавление умения:**
```python
@app.post("/skill")  
def skills_create(skill: SkillDefault, session=Depends(get_session)):  
    skill = Skill.model_validate(skill)  
    session.add(skill)  
    session.commit()  
    session.refresh(skill)  
    return {"status": 200, "data": skill}
```

- **Получение списка умений:**
```python
@app.get("/skills_list")  
def skills_list(session=Depends(get_session)) -> List[Skill]:  
    return session.exec(select(Skill)).all()
```

- **Обновление умения:**
```python
@app.patch("/skill/{skill_id}")  
def skill_update(  
        skill_id: int, skill: SkillDefault, session=Depends(get_session)  
) -> SkillDefault:  
    db_skill = session.get(Skill, skill_id)  
    if not db_skill:  
        raise HTTPException(status_code=404, detail="Skill not found")  
  
    skill_data = skill.model_dump(exclude_unset=True)  
    for key, value in skill_data.items():  
        setattr(db_skill, key, value)  
  
    session.add(db_skill)  
    session.commit()  
    session.refresh(db_skill)  
    return db_skill
```

- **Удаление умения:**
```python
@app.delete("/skill/{skill_id}")  
def skill_delete(skill_id: int, session=Depends(get_session)):  
    skill = session.get(Skill, skill_id)  
    if not skill:  
        raise HTTPException(status_code=404, detail="Skill not found")  
    session.delete(skill)  
    session.commit()  
    return {"ok": True}
```

- **Привязка умения к воину:**
```python
@app.post("/skill_warriors")  
def warrior_skill_add(skill_warrior: SkillWarriorLink, session=Depends(get_session)):  
    skill = session.get(Skill, skill_warrior.skill_id)  
    if not skill:  
        raise HTTPException(status_code=404, detail="Skill not found")  
  
    warrior = session.get(Warrior, skill_warrior.warrior_id)  
    if not warrior:  
        raise HTTPException(status_code=404, detail="Warrior not found")  
  
    if skill not in warrior.skills:  
        session.add(skill_warrior)  
        session.commit()  
  
    return {"ok": True}
```

## Результат

Все эндпоинты протестированы через документацию FastAPI. Пример вложенного ответа для воина:

![Пример вложенного ответа для воина](../assets/pr-2/warrior.png)

![Документация FastAPI](../assets/pr-2/FastAPI-docs.png)