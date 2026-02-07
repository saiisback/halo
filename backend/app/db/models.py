"""
Database Models for Halo

Stores project history, deployments, and user data.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, Text, DateTime, Integer, JSON, ForeignKey, Boolean
from sqlalchemy.orm import relationship, DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all models"""
    pass


class Project(Base):
    """A generated DApp project"""
    
    __tablename__ = "projects"
    
    id = Column(String(36), primary_key=True)
    prompt = Column(Text, nullable=False)
    template_type = Column(String(50), nullable=False)
    contract_id = Column(String(128), nullable=True)
    network = Column(String(20), default="testnet")
    status = Column(String(20), default="pending")  # pending, building, deployed, failed
    
    # Generated code (JSON with file contents)
    contract_code = Column(JSON, nullable=True)
    frontend_code = Column(JSON, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_wallet = Column(String(128), nullable=True)
    
    # Relationships
    build_logs = relationship("BuildLog", back_populates="project", cascade="all, delete-orphan")


class BuildLog(Base):
    """Build log entries for a project"""
    
    __tablename__ = "build_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    step = Column(String(50), nullable=False)
    message = Column(Text, nullable=True)
    log_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="build_logs")


class Deployment(Base):
    """Record of contract deployments"""
    
    __tablename__ = "deployments"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    contract_id = Column(String(128), nullable=False, unique=True)
    wasm_hash = Column(String(128), nullable=True)
    network = Column(String(20), nullable=False)
    deployer_address = Column(String(128), nullable=True)
    owner_address = Column(String(128), nullable=True)
    deployed_at = Column(DateTime, default=datetime.utcnow)
    
    # Contract metadata
    contract_name = Column(String(100), nullable=True)
    template_type = Column(String(50), nullable=True)


class DocumentChunk(Base):
    """Cached documentation chunks for RAG"""
    
    __tablename__ = "document_chunks"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    doc_type = Column(String(50), nullable=False)  # soroban-sdk, stellar-sdk-js, etc.
    source_url = Column(String(512), nullable=True)
    content = Column(Text, nullable=False)
    embedding_id = Column(String(100), nullable=True)  # ChromaDB document ID
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
