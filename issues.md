# Voice Assistant - Feature Implementation Issues

## Overview
This document outlines the features to be implemented for the Voice Assistant (Jarvis) project. Each issue is standalone and can be independently tackled by AI tools.

---

## Issue #1: Mode System Implementation

### Title
User-Defined Voice Activation Modes

### Description
Implement a feature where users can manually create custom modes (e.g., "coding mode", "gaming mode", "work mode") and add links and applications to each mode. When the user speaks "jarvis open [mode_name]", the assistant automatically opens all applications and URLs associated with that mode.

### Current State
- The system currently opens individual apps/websites via `openCommand()` function in `features.py`
- App commands are stored in SQLite database (`sys_command` table)
- Web commands are stored in SQLite database (`web_command` table)
- No grouping or mode-based organization exists

### Requirements

#### Backend
1. **Database Schema Modification**
   - Create a new `modes` table with columns:
     - `id` (INTEGER PRIMARY KEY)
     - `mode_name` (VARCHAR UNIQUE) - e.g., "coding mode", "gaming mode"
     - `description` (TEXT) - optional description
     - `created_at` (TIMESTAMP)
   
   - Create a junction table `mode_items` to link modes to apps/links:
     - `id` (INTEGER PRIMARY KEY)
     - `mode_id` (FOREIGN KEY → modes.id)
     - `item_type` (VARCHAR) - either "app" or "link"
     - `item_id` (FOREIGN KEY) - references either sys_command.id or web_command.id
     - `order` (INTEGER) - execution order

2. **Core Functions in `engine/features.py`**
   - `create_mode(mode_name, description="")` - Create a new mode
   - `add_to_mode(mode_name, item_type, command_name_or_url)` - Add app/link to mode
   - `remove_from_mode(mode_name, item_id)` - Remove item from mode
   - `activate_mode(mode_name)` - Execute all items in a mode sequentially with 1-2s delays
   - `list_modes()` - Return all available modes
   - `delete_mode(mode_name)` - Delete entire mode
   - `get_mode_items(mode_name)` - Get all items in a mode

3. **Voice Command Integration in `engine/command.py`**
   - Add command handlers for:
     - "open [mode_name]" → triggers `activate_mode()`
     - "create mode [mode_name]" → triggers `create_mode()`
     - "add [app_name/link] to [mode_name]" → triggers `add_to_mode()`
     - "show modes" / "list modes" → triggers `list_modes()`
   - Integrate with existing `allCommands()` processing logic

#### Frontend (UI)
1. **Web UI Components in `templates/`**
   - Add a new "Modes" section to the interface
   - Display list of existing modes with edit/delete buttons
   - Add modal/form to create new modes
   - Add interface to manage items in each mode (add/remove apps and links)
   - Visual indicator showing which mode is currently active

2. **JavaScript Integration**
   - Create mode management functions in `templates/main.js`
   - Handle mode creation, deletion, and item management
   - Send requests to backend via Eel exposed functions

#### Integration Points
- Modify `command.py` allCommands() to recognize mode-related voice commands
- Update database connection logic in `features.py` to handle new tables
- Ensure sequential execution with proper error handling (skip failed items)

### Success Criteria
- ✅ User can create custom modes via voice command or UI
- ✅ User can add multiple apps/links to a mode
- ✅ Voice command "jarvis open [mode_name]" opens all associated apps/links in sequence
- ✅ Mode data persists in database across sessions
- ✅ UI shows all modes and allows management
- ✅ Mode items are executed with proper delays to prevent system overload

### Files to Modify/Create
- `engine/features.py` - Add mode functions
- `engine/command.py` - Add mode command handlers
- `engine/db.py` - Database schema updates (commented out, needs implementation)
- `templates/main.js` - Frontend mode management
- `templates/index.html` - UI for mode management
- `templates/style.css` - Styling for mode interface

### Implementation Complexity
- **Difficulty**: Medium
- **Estimated Effort**: 8-12 hours

---

## Issue #2: Code Generator - Performance & Completeness Optimization

### Title
Improve Full-Stack Project Generation Speed and File Completeness

### Description
The current code generator in `code_generator.py` uses sequential file generation with delays, which is slow and sometimes produces incomplete projects. Optimize the generation process to:
- Generate all files within a reasonable timeframe (target: <5 minutes for a complete project)
- Guarantee 100% file completeness without missing any necessary files
- Ensure all generated files are immediately functional without requiring post-generation modifications

### Current State
- Located in: `engine/code_generator.py`
- Current approach:
  - Sequential file generation (1 file at a time)
  - 0.5s delay between files to avoid Gemini rate limiting
  - 3 retries per failed file
  - MongoDB connection injection is guaranteed
  - Takes 10-15+ minutes for a full-stack project

### Problems
1. **Speed**: Sequential generation + delays = very slow
2. **Completeness**: Missing files (e.g., package.json scripts, env files, error handlers, validation schemas)
3. **Configuration**: Many generated projects lack proper configuration files
4. **Dependencies**: Generated projects sometimes have missing or incorrect dependency declarations

### Requirements

#### Architecture Changes
1. **Batch Generation Strategy**
   - Group related files (e.g., all API routes together, all models together)
   - Use Gemini's batch API or implement smart request queuing to respect rate limits
   - Parallelize non-dependent file generation where possible
   - Implement intelligent retry logic with exponential backoff

2. **Enhanced File Specification**
   - Create a comprehensive file template library in `code_generator.py`:
     - Backend configuration files (.env, config files)
     - Frontend build configuration (webpack, vite, next.config)
     - Package management (package.json, requirements.txt with exact versions)
     - Docker files if applicable
     - Testing setup (Jest, pytest templates)
     - CI/CD configuration (GitHub Actions, etc.)
   
3. **Validation & Verification**
   - After generation, validate each file:
     - Syntax checking (Python AST, JavaScript/TypeScript parsing)
     - Completeness check (required imports, proper exports)
     - Dependency resolution (ensure all imports are in package.json/requirements.txt)
     - File structure validation (correct folder hierarchy)
   
   - If validation fails, trigger targeted re-generation for specific files only

4. **Project Completeness Checklist**
   - Frontend requirements:
     - Main entry file (index.js/main.tsx)
     - Component structure
     - Styling files
     - Package.json with all dependencies
     - Build configuration (if applicable)
     - .gitignore, README.md
   
   - Backend requirements:
     - Main server/app file
     - Routes/endpoints
     - Models/schemas
     - Database connection
     - Middleware
     - Error handling
     - Environment configuration
     - Package.json/requirements.txt
   
   - Root-level requirements:
     - .gitignore
     - README.md with setup instructions
     - docker-compose.yml (if Docker stack detected)
     - .env.example

#### Implementation Details

1. **Modify `_get_file_specs()` function**
   - Currently returns a flat list of files
   - Enhance to include dependency information
   - Organize files into dependency groups
   - Ensure all critical files are included

2. **Create `validate_generated_file()` function**
   - Takes file path and content
   - Performs syntax validation
   - Checks for required patterns/imports
   - Returns validation report

3. **Create `verify_project_completeness()` function**
   - Iterates through all generated files
   - Checks against completeness checklist
   - Identifies missing critical files
   - Triggers re-generation for missing files

4. **Implement `smart_generate_with_batching()` function**
   - Replace sequential generation
   - Group files by dependency level
   - Generate level 0 (no dependencies) in parallel
   - Wait for completion, then generate level 1, etc.
   - Implement rate limit respecting queuing

5. **Enhance error handling**
   - Better error messages during generation
   - Graceful degradation (generate what's possible)
   - Detailed logging of what failed and why

#### Performance Targets
- Single-page app: < 2 minutes
- Full-stack (MERN): < 4 minutes
- Full-stack with testing setup: < 5 minutes

### Success Criteria
- ✅ Project generation completes in < 5 minutes
- ✅ All required files are generated without missing critical files
- ✅ Generated projects run immediately after generation (no missing dependencies)
- ✅ Generated files pass syntax validation
- ✅ Database connections are properly configured
- ✅ All imports reference declared dependencies
- ✅ User receives completion report with file count and validation status

### Files to Modify/Create
- `engine/code_generator.py` - Main refactoring
- (Optional) `engine/validators.py` - New file for validation logic

### Implementation Complexity
- **Difficulty**: High
- **Estimated Effort**: 16-24 hours

---

## Issue #3: AI Model Training Integration in Code Generator

### Title
Automatic Model Training and Dataset Integration in Generated Projects

### Description
Extend the code generator to automatically:
1. Search for and download relevant datasets based on project requirements
2. Generate model training scripts that use those datasets
3. Train the models during project generation (or create ready-to-run training scripts)
4. Generate and save trained model files (.pkl, .h5, .pt, etc.)
5. Integrate the trained models into the project's backend

### Current State
- Code generator currently only creates project structure and basic code
- No dataset integration or model training
- No ML pipeline generation

### Requirements

#### Dataset Discovery & Management
1. **Create `dataset_finder.py` module**
   - Use APIs to search for relevant datasets:
     - Kaggle API (via `kaggle` package)
     - Hugging Face Datasets
     - UCI Machine Learning Repository
     - Google Dataset Search (via web scraping or API)
   
   - Function signatures:
     - `find_datasets(project_type, keywords)` - Search for datasets
     - `download_dataset(dataset_id, source)` - Download dataset to `data/` folder
     - `validate_dataset(path)` - Check dataset integrity
     - `get_dataset_info(dataset_id)` - Return schema, size, columns

2. **Dataset Selection Logic**
   - When user specifies ML project, prompt/analyze:
     - "What type of data? (image/text/tabular/time-series)"
     - "What's your use case? (classification/regression/clustering/detection)"
   
   - Auto-select appropriate public datasets

#### Model Training Pipeline
1. **Create `model_trainer.py` module**
   - Support multiple ML frameworks:
     - scikit-learn (for traditional ML)
     - TensorFlow/Keras (for deep learning)
     - PyTorch (for deep learning)
     - XGBoost (for gradient boosting)
   
   - Functions:
     - `generate_training_script(project_type, dataset_path, framework)` - Create train.py
     - `train_model(script_path, dataset_path)` - Execute training
     - `save_model(model, path, framework)` - Save trained model
     - `generate_inference_script(model_path, framework)` - Create prediction script

2. **Training Script Generation**
   - Auto-generate training scripts that include:
     - Data loading and preprocessing
     - Exploratory data analysis (EDA) code
     - Model architecture definition
     - Training loop with validation
     - Model evaluation metrics
     - Loss/accuracy plotting
     - Model saving and loading utilities

#### Integration with Code Generator
1. **Modify `handleCodeGeneration()` function**
   - Detect if ML/AI project is requested
   - If yes, trigger dataset discovery
   - Generate model training scripts
   - Execute training (if requested)
   - Save trained models to project structure
   - Integrate model paths into backend code

2. **Enhanced File Specs**
   - Add ML-specific files to generation pipeline:
     - `train.py` - Training script
     - `inference.py` - Model inference/prediction
     - `data_preprocessing.py` - Data handling utilities
     - `model_evaluation.py` - Metrics and visualization
     - `requirements-ml.txt` - ML-specific dependencies
     - `models/` directory - Store trained model files

3. **Backend Integration**
   - Generate API endpoints that use trained models:
     - `/api/predict` - Takes input, returns model prediction
     - `/api/model/stats` - Returns model performance metrics
     - `/api/train` - Trigger retraining (optional)

#### User Interaction Flow
```
User: "Generate a ML project for image classification"
↓
Assistant: "Found Kaggle dataset 'CIFAR-10'. Download? (Y/N)"
↓
Assistant: "Select model: simple-cnn, resnet, mobilenet? (list options)"
↓
Assistant: "Training now... [shows progress]"
↓
Assistant: "Training complete! Model accuracy: 95%. Project ready in /path"
```

### Success Criteria
- ✅ System can auto-discover relevant datasets
- ✅ Appropriate datasets are downloaded to project
- ✅ Training scripts are generated with proper structure
- ✅ Models train successfully and are saved
- ✅ Trained models integrate into backend APIs
- ✅ Users can request re-training without regenerating entire project
- ✅ Generation time includes training time (inform user of wait time)

### Files to Create/Modify
- `engine/dataset_finder.py` - New module for dataset discovery
- `engine/model_trainer.py` - New module for training pipeline
- `engine/code_generator.py` - Modifications to integrate ML training
- `requirements.txt` - Add ML packages (tensorflow, torch, sklearn, kaggle, etc.)

### External Dependencies
- kaggle (Kaggle API)
- huggingface_hub
- scikit-learn
- tensorflow or torch (one or both)
- xgboost

### Implementation Complexity
- **Difficulty**: Very High
- **Estimated Effort**: 24-40 hours

---

## Issue #4: Avatar Creation Feature

### Title
Implement AI-Powered Avatar Creation and Personalization

### Description
Create a feature that allows users to generate and customize AI avatars (3D or 2D character models) that represent the assistant or their personal assistant. Avatars should be customizable and displayable in the UI.

### Current State
- No avatar system currently exists
- UI displays basic interface without character representation
- `virtual_tryon.py` exists but uses it for clothing try-on, not avatar creation

### Requirements

#### Avatar Generation Pipeline
1. **Create `avatar_generator.py` module**
   - Support multiple avatar creation methods:
     - **Text-to-Image**: Generate avatar from text description using stable diffusion or DALL-E
     - **Parametric Generation**: Build avatar from customizable parameters (hair, face, clothing)
     - **3D Models**: Generate 3D character models using ready-made libraries
   
   - Functions:
     - `generate_avatar_from_description(description)` - Create from text prompt
     - `generate_avatar_from_parameters(params_dict)` - Create from configuration
     - `apply_avatar_style(style_name)` - Apply predefined style
     - `save_avatar(avatar_path)` - Save generated avatar

2. **Avatar Customization System**
   - Support customizing:
     - Face features (skin tone, eye color, hair style, facial hair)
     - Clothing and accessories
     - Background/environment
     - Animation style (static, idle animations)
     - Voice characteristics (already partially supported)
   
   - Store customization profiles:
     - Database table `avatars`:
       - `id` (PRIMARY KEY)
       - `name` (VARCHAR) - Avatar name
       - `description` (TEXT) - Avatar description
       - `image_path` (VARCHAR) - Path to avatar image
       - `model_path` (VARCHAR) - Path to 3D model (if applicable)
       - `customization_json` (JSON) - Stored parameters
       - `created_at` (TIMESTAMP)
       - `is_active` (BOOLEAN) - Currently active avatar

#### Avatar Display in UI
1. **Frontend Integration in `templates/`**
   - Display avatar in main UI:
     - Show active avatar in top-right or center area
     - Animate avatar on recognition/speaking (mouth movement, blinking)
     - Show avatar reacting to commands
   
   - Create avatar management panel:
     - Browse generated avatars
     - Activate/deactivate avatars
     - Customize existing avatars
     - Delete avatars

2. **Avatar Animation**
   - Implement idle animations (blinking, slight head movements)
   - Add speaking animation (lip-sync with audio)
   - Add reaction animations (happy, confused, thinking)
   - Use CSS animations or three.js for 3D models

#### Implementation Options

**Option A: 2D Avatar (Easier)**
- Use Stable Diffusion API (Hugging Face) or DALL-E
- Generate PNG/JPG avatar images
- Animate with CSS and JavaScript
- Less resource-intensive

**Option B: 3D Avatar (More Complex)**
- Use Ready Player Me API for 3D avatars
- Use three.js to display 3D models
- Add animations for mouth movement and expressions
- More impressive but resource-intensive

**Option C: Hybrid**
- Use 2D for simple profiles
- Support 3D import/display for advanced users

#### Voice-Avatar Synchronization
1. **Lip Sync Implementation**
   - Analyze TTS audio to determine phonemes
   - Map phonemes to mouth shapes
   - Animate avatar mouth during speech
   - Tools: `librosa` (audio analysis), custom phoneme mapper

2. **Avatar Reactions**
   - Detect command type and show appropriate reaction
   - Thinking animation during processing
   - Success/error animations based on command result

### Success Criteria
- ✅ User can generate custom avatars via voice or UI
- ✅ Avatar is displayed in the main UI
- ✅ Avatar customization options work (appearance, style)
- ✅ Avatar shows idle animations
- ✅ Avatar animates while speaking (lip-sync or simple animation)
- ✅ Multiple avatars can be created and switched
- ✅ Avatar data persists in database

### Files to Create/Modify
- `engine/avatar_generator.py` - New module
- `templates/index.html` - Avatar display area
- `templates/style.css` - Avatar styling and animations
- `templates/main.js` - Avatar display and interaction logic
- `engine/features.py` - Add avatar management functions
- `engine/command.py` - Add avatar-related voice commands

### External Dependencies (Choose based on approach)
- For 2D: `diffusers` (Stable Diffusion), `PIL`
- For 3D: `three.js` (frontend), `trimesh` or `pyvista` (backend)
- For Audio-to-Phoneme: `librosa`, `g2p-en`

### Implementation Complexity
- **Difficulty**: Medium-High (depends on 2D vs 3D choice)
- **Estimated Effort**: 12-20 hours (2D), 20-30 hours (3D/Hybrid)

---

## Issue #5: News Aggregator Feature

### Title
Integrate News Aggregator for Voice-Based News Updates

### Description
Implement a news aggregation feature that allows users to:
- Request news updates via voice commands (e.g., "Show me technology news")
- Customize news sources and categories
- Receive summarized news with text-to-speech
- Store favorite news articles
- Display news in the UI with filtering and search

### Current State
- No news aggregation feature exists
- No news data sources integrated

### Requirements

#### News Data Sources
1. **Create `news_aggregator.py` module**
   - Integrate multiple news APIs:
     - NewsAPI (https://newsapi.org) - Comprehensive news coverage
     - BBC News API (if available) - Quality journalism
     - New York Times API - Premium content
     - RSS Feeds - Customizable sources
   
   - Support news categories:
     - Technology, Business, Sports, Health, Entertainment, Science, Politics
     - Custom keywords/topics

2. **Functions to Implement**
   - `fetch_news(category, limit, source)` - Fetch news articles
   - `search_news(keyword, date_range)` - Search news by topic
   - `get_trending_news()` - Get trending articles
   - `summarize_article(article_text)` - Create short summary
   - `filter_news(news_list, filters)` - Filter by date, source, sentiment
   - `get_news_by_source(source)` - Get news from specific source

#### Database Schema
1. **Create news-related tables**
   ```sql
   CREATE TABLE news_sources (
       id INTEGER PRIMARY KEY,
       name VARCHAR(100),
       api_key VARCHAR(500),
       category VARCHAR(50),
       is_active BOOLEAN
   );
   
   CREATE TABLE saved_articles (
       id INTEGER PRIMARY KEY,
       title VARCHAR(500),
       summary TEXT,
       source VARCHAR(100),
       url VARCHAR(1000),
       category VARCHAR(50),
       saved_at TIMESTAMP,
       user_notes TEXT
   );
   
   CREATE TABLE news_preferences (
       id INTEGER PRIMARY KEY,
       user_id INTEGER,
       preferred_categories VARCHAR(500),
       preferred_sources VARCHAR(500),
       daily_digest_time TIME,
       summary_length VARCHAR(20)  -- short, medium, long
   );
   ```

#### Voice Command Integration
1. **Add News Commands to `command.py`**
   - "Show me [category] news"
   - "Search news about [topic]"
   - "What's trending?"
   - "Save this article"
   - "Show my saved articles"
   - "Read news [summary|full]"
   - "Set up daily news digest"

2. **Smart Response Generation**
   - Fetch relevant news based on user query
   - Summarize articles (long articles → short summaries)
   - Use TTS to read summaries aloud
   - Provide links in UI

#### Frontend UI Components
1. **Create News Panel in `templates/`**
   - News display section in main UI:
     - Article title, snippet, source
     - Publication date
     - Read full article, save article buttons
     - Category tags
   
   - News management interface:
     - Configure news sources
     - Set preferences (categories, summary length)
     - Set daily digest time
     - View saved articles

2. **News Display Features**
   - Auto-refresh news at intervals (every 30 min, 1 hour, etc.)
     - Category filtering
     - Source filtering
     - Date range filtering
     - Search functionality

#### Implementation Features

1. **Summarization**
   - Use extractive summarization (select key sentences)
   - Option: Use generative summarization for better results
   - Configurable summary length (short/medium/long)

2. **Daily News Digest**
   - Option to get daily digest at set time
   - Aggregate top articles from preferred categories
   - Read digest aloud or show as text
   - Email digest (optional)

3. **Sentiment Analysis** (Optional Enhancement)
   - Analyze article sentiment (positive, negative, neutral)
   - Display sentiment indicators
   - Filter by sentiment

4. **Caching**
   - Cache fetched news to reduce API calls
   - Clear cache every 30 minutes or on demand
   - Store fetched articles in database for quick access

### Success Criteria
- ✅ User can request news via voice commands
- ✅ News is fetched from multiple sources
- ✅ News is displayed and summarized in UI
- ✅ User can filter news by category and source
- ✅ User can save articles for later reading
- ✅ TTS reads news summaries aloud
- ✅ Daily digest feature works
- ✅ User preferences are saved and persisted

### Files to Create/Modify
- `engine/news_aggregator.py` - New module for news fetching and management
- `engine/news_summarizer.py` - New module for article summarization (optional)
- `engine/command.py` - Add news command handlers
- `engine/features.py` - Add news-related exposed functions
- `templates/index.html` - News UI components
- `templates/style.css` - News styling
- `templates/main.js` - News frontend logic

### External Dependencies
- newsapi (NewsAPI client library)
- feedparser (RSS feed parsing)
- transformers (for advanced summarization, optional)
- textblob or vader (for sentiment analysis, optional)

### API Keys Required
- NewsAPI key (https://newsapi.org - free tier available)
- New York Times API key (optional, for premium content)

### Implementation Complexity
- **Difficulty**: Medium
- **Estimated Effort**: 12-16 hours

---

## Implementation Priority & Roadmap

### Phase 1 (Foundational)
1. **Issue #1: Mode System** ⭐⭐⭐
   - Most impactful for user experience
   - Builds on existing database structure
   - Moderate complexity

2. **Issue #5: News Aggregator** ⭐⭐
   - Good for engagement
   - Standalone feature (no dependencies)
   - Medium complexity

### Phase 2 (Enhancement)
3. **Issue #2: Code Generator Optimization** ⭐⭐⭐
   - Critical for project quality
   - Improves user satisfaction
   - High complexity but high impact

### Phase 3 (Advanced)
4. **Issue #3: Model Training Integration** ⭐⭐
   - Advanced ML capability
   - Builds on Issue #2
   - Very high complexity

5. **Issue #4: Avatar Creation** ⭐⭐⭐
   - Enhances UI/UX significantly
   - Moderate-to-high complexity
   - Great for marketing/presentation

---

## Notes for Implementation Teams

### Testing Strategy
- Unit tests for each new module
- Integration tests with existing features
- Voice command testing for command.py changes
- Database migration testing (especially for schema changes)
- UI/UX testing for frontend components

### Documentation Needed
- API documentation for new functions
- Database schema documentation
- Voice command reference guide
- User guide for new features
- Developer setup guide for dependencies

### Deployment Considerations
- Database migrations for schema changes
- Backward compatibility (legacy commands should still work)
- Graceful degradation (features should work even if APIs are unavailable)
- Performance monitoring for new features
- Rate limiting awareness (especially for external APIs)

### API Keys & Secrets
- Store all API keys in `.env` file
- Never commit API keys to repository
- Document which API keys are needed for each feature
- Provide `.env.example` with placeholder keys

### Performance Monitoring
- Log execution times for new features
- Monitor database query performance with new tables
- Track API rate limit usage
- Alert on failures or timeouts

---

## Conclusion

These five features collectively enhance the Voice Assistant with powerful capabilities:
- **Productivity** (Mode System, Code Generator)
- **Intelligence** (Model Training, News Aggregator)
- **User Experience** (Avatar Creation)

Each can be developed independently and integrated into the main codebase with proper testing and documentation.
