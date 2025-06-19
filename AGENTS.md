# AGENTS.md - MTG Deck Builder

## Project Overview
This is a Magic: The Gathering deck builder application built with Python, Flask, and Gradio. The application allows users to build decks using YAML configuration files, manage card collections, and analyze deck performance.

## Architecture Guidelines

### Core Components
- **Database Layer**: SQLAlchemy ORM with repository pattern
- **YAML Deck Builder**: Configuration-driven deck building system
- **Gradio UI**: Web-based interface for deck management
- **MTGJSON Integration**: Card data synchronization from MTGJSON

### Project Structure
```
MTGDecks/
├── mtg_deck_builder/          # Core deck building logic
│   ├── db/                    # Database models and repositories
│   ├── models/                # Data models and business logic
│   └── yaml_builder/          # YAML configuration processing
├── mtg_deckbuilder_ui/        # Gradio-based user interface
│   ├── ui/                    # UI components and layouts
│   ├── logic/                 # UI callback functions
│   └── utils/                 # Utility functions
├── tests/                     # Test suite
├── deck_configs/              # YAML deck configuration files
└── requirements.txt           # Python dependencies
```

## Coding Standards

### Python Best Practices
- **Code Formatting**: Use Black with 88 character line length
- **Import Sorting**: Use isort for consistent import organization
- **Type Hints**: Use type hints for all function parameters and returns
- **Naming Conventions**:
  - `snake_case` for functions and variables
  - `PascalCase` for classes
  - `UPPER_CASE` for constants
- **Documentation**: Use Google-style docstrings for all public APIs

### Database Guidelines
- **Repository Pattern**: All database access goes through repository interfaces
- **Models**: Define in `mtg_deck_builder/db/models.py`
- **Relationships**: Use proper SQLAlchemy relationships
- **Migrations**: Use Alembic for database schema changes
- **Connection Management**: Implement proper connection pooling

### YAML Configuration System
- **Schema Validation**: All YAML configs must validate against schema in `/README.yaml.md`
- **DeckConfig Objects**: Convert all YAML configs to `DeckConfig` before use
- **Context Tracking**: Use `DeckBuildContext` for tracking build state
- **Category Rules**: Use `CategoryDefinition` for card selection rules
- **Scoring System**: Use `ScoringRulesMeta` for card evaluation

## Development Workflow

### Testing Strategy
- **Framework**: Use pytest for all testing
- **Coverage**: Aim for comprehensive test coverage
- **Fixtures**: Use pytest fixtures for test data setup
- **Mocking**: Use pytest-mock for external dependencies
- **Test Organization**: Group tests by functionality

### Error Handling
- **Custom Exceptions**: Create specific exception classes
- **Logging**: Implement proper logging throughout the application
- **User Feedback**: Use Gradio's error system for UI feedback
- **Validation**: Validate inputs at all layers

### Performance Considerations
- **Database Queries**: Optimize with proper indexing and query patterns
- **Caching**: Implement caching for frequently accessed data
- **Background Tasks**: Use background processing for heavy operations
- **Connection Pooling**: Use proper database connection management

## UI Guidelines

### Gradio Components
- **Version**: Use Gradio 5.32.1
- **Layout**: Organize components logically with proper spacing
- **Validation**: Implement real-time validation for user inputs
- **Feedback**: Use `gr.Info()` and `gr.Error()` for user feedback
- **Progress**: Show progress bars for long-running operations

### Component Organization
- **Tabs**: Use tabs for different functional areas
- **Reusability**: Create reusable component groups
- **State Management**: Separate logic from display components
- **Theming**: Use consistent theming throughout the application

## Common Patterns

### Repository Pattern
```python
class SampleRepository(BaseRepository):
    def filter_cards(
        self,
        name_query: Optional[str] = None,
        text_query: Optional[str] = None,
        rarity: Optional[str] = None,
        basic_type: Optional[str] = None,
        type_text: Optional[Union[str, List[str]]] = None,  # Keep for backward compatibility
        supertype: Optional[str] = None,
        subtype: Optional[str] = None,
        keyword_multi: Optional[List[str]] = None,
        type_query: Optional[Union[str, List[str]]] = None,
        colors: Optional[List[str]] = None,
        color_identity: Optional[List[str]] = None,
        color_mode: str = "subset",
        legal_in: Optional[List[str]] = None,
        add_where: Optional[str] = None,
        exclude_type: Optional[List[str]] = None,
        names_in: Optional[List[str]] = None,
        min_quantity: int = 0,
        allow_colorless: bool = False,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> 'SampleCardRepository':

    
```

### YAML Deck Building
```python
# 1. Parse and validate YAML config
deck_config = DeckConfig.from_yaml(yaml_content)


# 2. Initialize build context
deck_build_context = DeckBuildContext(
    config=deck_config,
    summary_repo=summary_repo,
    deck=deck
)
build_context = BuildContext(
    deck_config=deck_config,
    summary_repo=summary_repo,
    callbacks=callbacks,
    deck_build_context=deck_build_context
)


# 3. Build deck using context
deck_builder = YamlDeckBuilder()
deck = deck_builder.build_deck(context)
```

### UI Component Pattern
```python
def create_deck_builder_tab():
    with gr.Tab("Deck Builder"):
        with gr.Row():
            yaml_input = gr.Code(label="YAML Configuration")
            build_button = gr.Button("Build Deck")
        
        with gr.Row():
            deck_output = gr.Dataframe(label="Generated Deck")
```

## Technology Stack

### Core Dependencies
- **Python**: 3.8+
- **Flask**: Web framework
- **SQLAlchemy**: ORM and database management
- **Gradio**: UI framework
- **PyYAML**: YAML processing
- **pytest**: Testing framework

### Development Tools
- **Black**: Code formatting
- **isort**: Import sorting
- **mypy**: Type checking
- **pylint**: Code linting
- **Alembic**: Database migrations

## Troubleshooting

### Common Issues
1. **Database Connection**: Check connection pooling and session management
2. **YAML Validation**: Ensure configs match schema requirements
3. **UI Responsiveness**: Use background tasks for heavy operations
4. **Memory Usage**: Monitor large dataset processing

### Debugging Tips
- Use proper logging throughout the application
- Implement comprehensive error handling
- Use pytest fixtures for test data
- Monitor database query performance

## API Guidelines

### RESTful Design
- Use proper HTTP status codes
- Implement consistent error responses
- Use JSON for data exchange
- Follow REST naming conventions

### Documentation
- Document all public APIs with docstrings
- Use type hints for function signatures
- Provide usage examples
- Keep README files updated

## Testing Strategy

### Test Organization
- **Unit Tests**: Test individual functions and classes
- **Integration Tests**: Test component interactions
- **End-to-End Tests**: Test complete workflows
- **Performance Tests**: Test system performance under load

### Test Data
- Use fixtures for consistent test data
- Mock external dependencies
- Test edge cases and error conditions
- Maintain test data in `tests/sample_data/`

## Deployment Guidelines

### Environment Setup
- Use virtual environments (venv)
- Pin dependency versions in requirements.txt
- Use environment variables for configuration
- Implement proper logging configuration

### Production Considerations
- Use proper database connection pooling
- Implement caching strategies
- Monitor application performance
- Set up proper error tracking

## Contributing Guidelines

### Code Review Process
- Follow established coding standards
- Write comprehensive tests
- Update documentation as needed
- Use meaningful commit messages

### Git Workflow
- Use feature branches for development
- Write descriptive commit messages
- Keep commits atomic and focused
- Use proper .gitignore patterns

---

**Note**: This document should be updated as the project evolves. Always refer to the latest version for current guidelines and best practices. 