from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

Base = declarative_base()

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sender = Column(String, nullable=False)
    recipient = Column(String, nullable=False)
    content = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    @staticmethod
    def save_message(session, sender, recipient, content):
        """Salva uma mensagem no banco de dados"""
        message = Message(sender=sender, recipient=recipient, content=content)
        session.add(message)
        session.commit()

    @staticmethod
    def get_messages_for_user(session, username):
        """Recupera mensagens pendentes para um usuário e as remove do banco"""
        messages = session.query(Message).filter_by(recipient=username).all()
        session.query(Message).filter_by(recipient=username).delete()
        session.commit()
        return [{"from": msg.sender, "message": msg.content, "timestamp": msg.timestamp} for msg in messages]

# Criar banco SQLite e sessão
engine = create_engine("sqlite:///chat.db")
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
