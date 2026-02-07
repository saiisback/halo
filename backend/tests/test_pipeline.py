"""
Integration tests for the Halo generation pipeline.

Run with: pytest tests/test_pipeline.py -v
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch


# Test the architect agent
class TestArchitectAgent:
    
    @pytest.mark.asyncio
    async def test_analyze_prompt_returns_spec(self):
        """Test that analyze_prompt returns a valid specification"""
        from app.agents.architect import analyze_prompt
        
        # Mock the LLM to return a valid response
        mock_response = '''{
            "template_type": "token_transfer",
            "spec": {
                "name": "TransferApp",
                "description": "Transfer tokens between addresses",
                "functions": [{"name": "transfer", "description": "Transfer tokens"}],
                "storage": {},
                "parameters": {},
                "ui_requirements": ["wallet_connect", "transfer_form"]
            }
        }'''
        
        with patch('app.agents.architect.generate_completion', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response
            
            result = await analyze_prompt("Create a fund transfer app")
            
            assert "template_type" in result
            assert "spec" in result
            assert "name" in result["spec"]
            assert "description" in result["spec"]


# Test frontend templates (contract templates removed)
class TestTemplates:
    
    def test_frontend_templates_exist(self):
        """Test that frontend components are available"""
        from app.templates.frontend import get_frontend_components
        
        components = get_frontend_components()
        assert "WalletConnect" in components
        assert "TxStatus" in components
        assert "BalanceDisplay" in components

    def test_frontend_template_css(self):
        """Test that frontend base template has CSS"""
        from app.templates.frontend import get_frontend_template
        
        template = get_frontend_template()
        assert "index_css" in template
        assert "background" in template["index_css"]


# Test Rust agent
class TestRustAgent:
    
    @pytest.mark.asyncio
    async def test_generate_contract_from_spec(self):
        """Test that rust agent generates valid contract code"""
        from app.agents.rust_agent import generate_rust_contract
        
        spec = {
            "name": "TestContract",
            "description": "A test contract",
            "functions": [{"name": "test", "description": "Test function"}],
            "storage": {},
            "parameters": {},
        }
        
        mock_code = '''#![no_std]
use soroban_sdk::{contract, contractimpl, Env};

#[contract]
pub struct TestContract;

#[contractimpl]
impl TestContract {
    pub fn test(env: Env) {
        // test
    }
}'''
        
        with patch('app.agents.rust_agent.generate_completion', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_code
            
            result = await generate_rust_contract(
                template_type="test",
                spec=spec,
                docs_context=[],
            )
            
            assert "lib_rs" in result
            assert "cargo_toml" in result
            assert "#![no_std]" in result["lib_rs"]
            assert "#[contract]" in result["lib_rs"]


# Test React agent
class TestReactAgent:
    
    def test_structural_validation(self):
        """Test structural validation of React code"""
        from app.agents.react_agent import check_structural_validity
        
        # Valid code
        valid_code = '''
import { useState } from 'react';

function App() {
    const [count, setCount] = useState(0);
    return <div>{count}</div>;
}

export default App;
'''
        assert check_structural_validity(valid_code) is None
        
        # Invalid code - missing export
        invalid_code = '''
import { useState } from 'react';

function App() {
    return <div>Hello</div>;
}
'''
        assert check_structural_validity(invalid_code) is not None


# Test RAG
class TestRAG:
    
    @pytest.mark.asyncio
    async def test_fallback_docs(self):
        """Test that fallback docs are returned when RAG unavailable"""
        from app.rag.retriever import get_fallback_docs
        
        soroban_docs = get_fallback_docs("soroban-sdk")
        assert len(soroban_docs) > 0
        assert any("Soroban" in doc for doc in soroban_docs)
        
        js_docs = get_fallback_docs("stellar-sdk-js")
        assert len(js_docs) > 0
        assert any("Freighter" in doc for doc in js_docs)


# Test configuration
class TestConfig:
    
    def test_settings_loaded(self):
        """Test that settings are properly loaded"""
        from app.core.config import settings
        
        assert settings.app_name == "Halo"
        assert settings.stellar_network == "testnet"
        assert settings.claude_model == "claude-sonnet-4-5-20250929"


# Integration test (requires running services)
class TestIntegration:
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires running LLM and Docker")
    async def test_full_pipeline(self):
        """Test the full generation pipeline"""
        from app.agents.orchestrator import run_pipeline
        
        events = []
        async for event in run_pipeline(
            prompt="Create a simple fund transfer app",
            network="testnet",
        ):
            events.append(event)
        
        # Check we got all expected steps
        steps = [e.get("step") for e in events]
        assert "analyzing" in steps
        assert "generating_rust" in steps
        assert "compiling" in steps or "error" in steps


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
