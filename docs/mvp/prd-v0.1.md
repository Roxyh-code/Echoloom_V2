我建议直接把这份文档作为 EchoLoom MVP v0.1 的开发 PRD，发给 Claude Code、Codex 或其他编程 AI。

这次我们把目标定得非常明确：

先做一个真正能运行的 Character Creation + Chat + Refinement 产品，而不是继续停留在技术研究或静态 UI Demo。

完整 MVP 包括四个关键体验：
1. Create：输入自然语言，生成结构化人物档案。
2. Chat：立即与人物进行多轮文字对话。
3. Refine：修改现有角色的性格、背景和说话方式，而不是重新创建。
4. Visualize：生成角色头像，并支持基于原有图片的修改。
语音、视频、多文档人格提取、复杂记忆系统暂时不做，但会在架构中预留扩展能力。

下面我会按照真正可以交给开发 AI 执行的 PRD 格式来写，包括功能细节、页面、技术架构、数据结构、API、开发顺序和验收标准。
EchoLoom MVP v0.1 — Product Requirements Document
Version 0.1 · November 2026 · Development-ready specification
EchoLoom MVP v0.1
Product Requirements Document (PRD)
Project: EchoLoom
Version: 0.1
Stage: Working MVP / Functional Prototype
Repository: https://github.com/Roxyh-code/Echoloom_V2
Primary Goal: Build a functional AI character creation, customization, and conversation platform using third-party AI APIs.

1. Product Overview
1.1 Vision
EchoLoom — Bring your favorite characters to life.

EchoLoom is an AI-powered character creation and interaction platform that allows users to create personalized fictional characters through natural language, customize their identities and appearances, and engage in ongoing conversations with them.

Unlike traditional character generators that produce a one-time output, EchoLoom focuses on persistent, editable character identities.

Users should be able to create a character once, continuously refine its personality and appearance, and return to interact with the same character.

The long-term vision is to develop a character identity and continuity platform capable of preserving characters across different models, applications, and interaction modalities.

However, MVP v0.1 focuses exclusively on building a functioning end-to-end character creation and interaction experience.
1.2 MVP Objective
The MVP must support the following complete workflow:

Describe → Generate → Review → Customize → Chat → Save → Return

A user should be able to:
1. Describe a fictional character in natural language.
2. Generate a structured Character Profile using an LLM.
3. Review and edit the generated personality and background.
4. Start a persistent text conversation with that character.
5. Generate an initial character portrait through an image API.
6. Modify the existing character portrait without necessarily regenerating it from scratch.
7. Make further changes to the character's profile using a form or natural-language instructions.
8. Save the character and return to continue the conversation.
Definition of Success
The MVP is successful when a user can complete the above journey without manually interacting with an AI API, editing code, or modifying database records.

All essential functionality must work end-to-end with real API integrations.

Static mockups or hardcoded AI responses do not qualify as a completed MVP.

2. Product Philosophy
2.1 Create Once, Refine Continuously
A character is not a disposable generation result.

Each generated character must have:
- A permanent character identifier.
- A structured, editable profile.
- A persistent conversation history.
- An optional visual identity.
- A history of profile changes.
- An image revision history.
Users must be able to edit an existing character without losing its previous conversation history.
2.2 User-Controlled Identity
The AI may suggest character attributes, but the user has final control over them.

An AI-generated profile is a starting point, not an immutable definition.

The user can modify, accept, reject, or overwrite AI suggestions.
2.3 Modular AI Architecture
EchoLoom must not depend entirely on one AI provider.

LLM services and image generation services should be implemented as separate, replaceable modules.

The application must maintain its own character data independently of external AI providers.
2.4 Simple First, Expand Later
Prioritize a clean, intuitive user experience and reliable functionality over advanced features.

Do not introduce complex agent frameworks, vector databases, microservices, or custom-trained models unless clearly necessary.

3. Target Users and Primary Use Cases
3.1 Target Users
The initial audience includes:
- Users who want to create original fictional characters.
- Writers creating characters for stories.
- Role-playing and interactive storytelling enthusiasts.
- Users who want to interact with personalized AI companions.
- Users experimenting with character personalities and dialogue.
3.2 Primary Use Case
A user enters:
"I want to create a mysterious female librarian in her twenties. She has silver hair, blue eyes, and a quiet personality. She is intelligent, slightly sarcastic, and very interested in astronomy. She rarely expresses affection directly, but she genuinely cares about people close to her."

EchoLoom automatically generates:
- Character name.
- Short character description.
- Personality traits.
- Background story.
- Values and motivations.
- Speech style.
- Behavioral tendencies.
- Visual appearance description.
- Image generation prompt.
The user can review these fields, make adjustments, generate the character's portrait, and start chatting.
Expected Conversation
User: "What are you reading?"

Character: "A book about dying stars. Surprisingly cheerful material, isn't it?"

The response should reflect the character's established personality and speaking style.

4. MVP Feature Requirements
Feature F01 — Natural Language Character Creation
Priority: P0 — Required
Description
Provide a character creation interface where users can describe the character they want to create.

The primary input should be a large text box.
UI Requirements
The Create Character page should contain:
- Main heading: "Bring your character to life."
- Subtitle explaining the character creation process.
- Multiline character description field.
- "Create Character" button.
- Loading state.
- Error and retry handling.
Optional example prompts can be provided.
Functional Requirements
1. Accept free-form text input.
2. Validate that the input is not empty.
3. Apply a reasonable input length limit.
4. Send the description to the backend.
5. Use an LLM to generate a structured Character Profile.
6. Validate the generated output against a defined data schema.
7. Save the generated character to the database.
8. Display the generated profile in the Character Editor.
Important Behavior
The LLM should preserve user-specified facts.

For example, if the user specifies black hair, the generated profile must not silently change the hair color to blonde.

If the user leaves a field unspecified, the model may generate a reasonable suggestion.

Generated additions should be editable and distinguishable from explicit user requirements where practical.

Do not repeatedly regenerate the entire profile simply because a user wants to modify one attribute.

Feature F02 — Structured Character Profile
Priority: P0 — Required
Description
Every character must have a structured profile stored independently of the AI provider.
Suggested Initial Schema
{
  "character_id": "uuid",
  "name": "Evelyn",
  "short_description": "A quiet and mysterious librarian.",
  "appearance": {
    "age_description": "Young adult",
    "hair": "Long silver hair",
    "eyes": "Blue",
    "clothing": "Dark academic clothing",
    "other_details": ""
  },
  "personality": {
    "core_traits": [
      "Intelligent",
      "Reserved",
      "Sarcastic"
    ],
    "values": [
      "Loyalty",
      "Knowledge"
    ],
    "motivations": [
      "Understanding the universe"
    ],
    "behavioral_patterns": [
      "Shows affection through actions"
    ]
  },
  "backstory": "...",
  "speech_style": {
    "tone": "Calm and slightly sarcastic",
    "vocabulary": "Thoughtful and precise",
    "speaking_habits": []
  },
  "interaction_preferences": {
    "conversation_style": "Natural, character-driven",
    "relationship_context": ""
  },
  "visual_style": "Anime",
  "profile_version": 1
}
This is a starting schema, not a finalized personality ontology.

The developer may refine field names and types to ensure maintainability.
Requirements
- Use schema validation.
- Store the profile as structured data.
- Support partially populated fields.
- Do not require the AI to invent unknown personal history.
- Allow manual edits.
- Persist changes.
- Maintain stable character IDs.
- Track profile version changes.
Do not tightly couple the profile format to one LLM vendor's response structure.

Feature F03 — Character Profile Editor
Priority: P0 — Required
Description
After generation, users should see a structured, editable character profile.
Editable Sections
Basic Information
- Name.
- Short description.
- Background story.
Appearance
- Hair.
- Eyes.
- Clothing.
- Physical characteristics.
- Visual style.
Personality
- Core traits.
- Values.
- Motivations.
- Behavioral tendencies.
Speech and Interaction
- Speaking style.
- Tone.
- Typical expressions.
- Interaction preferences.
Editing Methods
The application must support two editing modes.
Mode A — Direct Editing
Users can manually edit individual fields.

Example:

Change:

Reserved, intelligent, caring

To:

Reserved, intelligent, emotionally distant

Save the changes without another LLM call.
Mode B — Refine with AI
Users can enter natural-language instructions such as:
"Make her more emotionally distant, but keep her gentle toward people she trusts."

The backend should:
1. Load the current profile.
2. Send the existing profile and user instruction to an LLM.
3. Generate a structured patch or updated field proposal.
4. Validate the proposal.
5. Show the proposed changes to the user.
6. Allow the user to accept or reject the modifications.
7. Save only approved changes.
Critical Requirements
- Do not create a new character when refining an existing character.
- Do not overwrite unrelated fields.
- Do not reset the conversation history.
- Do not change the character's image unless the user requests it.
- Support undo or restoration to the previous profile version.
- Show which fields have changed before confirmation.
Example:

User requests a more sarcastic personality.

Expected result:

Only personality-related fields are updated.

Appearance, backstory, name, and saved portrait remain unchanged unless the request explicitly affects them.

Feature F04 — Character Chat
Priority: P0 — Required
Description
Users must be able to have ongoing text conversations with their generated characters.
UI Requirements
The chat interface should include:
- Character portrait or placeholder.
- Character name.
- Scrollable chat history.
- User and character message bubbles.
- Message input.
- Send button.
- Response loading indicator.
- Character editing entry point.
Functional Requirements
1. Load the current Character Profile.
2. Retrieve relevant conversation history.
3. Construct the LLM instruction from the character profile.
4. Send the user message to the LLM.
5. Display the response.
6. Persist both user and assistant messages.
7. Restore the conversation after page refresh.
Character Consistency
The character should respond according to its current profile.

The model should preserve:
- Identity.
- Personality.
- Background.
- Speech style.
- Behavioral preferences.
- Established conversation context.
For MVP v0.1, use profile-based prompting and recent chat history.

Advanced long-term memory extraction is not required.
Conversation Context Strategy
Do not send unlimited conversation history to the LLM.

Implement a configurable context window.

Initially:
- Always include the current Character Profile.
- Include a limited set of recent messages.
- Reserve space for model output.
- Handle long conversations without exceeding API limits.
Older messages must remain saved in the database even if not included in the current model context.

Conversation summarization can be added later if needed.
Profile Modification During Chat
If a user edits a character's personality, future responses must use the updated profile.

Previous chat messages should remain unchanged.

Store the profile version associated with each assistant message where feasible.
Failure Handling
If an API request fails:
- Display an understandable error.
- Allow retry.
- Do not save failed assistant responses as successful messages.
- Avoid duplicate messages on retry.

Feature F05 — Character Image Generation
Priority: P1 — Required for the complete v0.1 MVP
Description
Generate an initial character portrait from the structured appearance profile.
Candidate Providers
- Ideogram image generation API.
- FLUX image generation API.
- OpenAI image generation API.
Implement a provider abstraction so the specific service can be changed through configuration.

Initial preference: Ideogram, subject to current API availability and a small practical comparison.
Requirements
1. Generate an image prompt from the Character Profile.
2. Allow the user to choose a visual style.
3. Request one initial portrait by default.
4. Display generation progress.
5. Save the generated image.
6. Associate the image with the character.
7. Allow the user to keep or discard it.
Visual Style Options
Initially support:
- Anime.
- Cartoon.
- Semi-realistic.
- Realistic.
These can be implemented as prompt presets.
Important Design Decision
Image generation should be an explicit action.

The character creation process must still work if the image provider is unavailable.

A user should be able to create and chat with a character without generating an image.
Image Storage
Store:
- Character ID.
- Image ID.
- Provider/model identifier.
- Generation prompt.
- Image storage path.
- Created timestamp.
- Revision number.
Do not rely on temporary provider-hosted image URLs as permanent storage.

Feature F06 — Character Image Editing
Priority: P1 — Required for the complete v0.1 MVP
Description
Allow users to modify an existing character portrait through natural-language instructions.

Example:
"Change her hair color to dark blue. Keep everything else the same."

Requirements
1. Load the currently selected portrait.
2. Accept a natural-language edit instruction.
3. Send the existing image and edit instruction to an image editing API.
4. Generate an edited version.
5. Preview the result.
6. Allow the user to accept or discard it.
7. Preserve the previous version.
8. Support restoration of earlier image versions.
Image Editing Modes
Mode A — Prompt-based Editing

User provides an instruction describing the desired change.

This is the minimum required implementation.

Mode B — Mask-based Editing

User selects a region of the image to modify.

The API should try to preserve unselected areas.

Mask-based editing is optional for v0.1 and can be deferred if implementation complexity is excessive.
Critical Requirements
- Do not overwrite the original image file.
- Save each accepted revision separately.
- Preserve access to earlier images.
- Avoid unnecessary full regeneration.
- Warn the user that image edits may unintentionally alter other details.
Image Version Example
Character Evelyn
  image_v1.png
    └── image_v2.png
          └── image_v3.png
A character may have multiple image versions while retaining one continuous character identity.

Feature F07 — Character Library
Priority: P0 — Required
Description
Users should be able to access previously created characters.
Requirements
The library should display character cards containing:
- Portrait or placeholder.
- Character name.
- Short description.
- Last updated timestamp.
Actions:
- Open character.
- Continue chat.
- Edit character.
- Delete character.
A basic grid layout is sufficient.

For the initial local prototype, a single-user library is acceptable.

Full account authentication is not required until the application is deployed for multiple independent users.

Feature F08 — Character Persistence and Versioning
Priority: P0 — Required
Requirements
All character information must persist after refreshing or restarting the application.

Store:
- Character profiles.
- Profile revision history.
- Conversations.
- Messages.
- Images.
- Image revisions.
- Creation and modification timestamps.
The user must not lose their character when switching between editing and chatting.

Profile editing and image editing should use independent revision histories.

5. Out of Scope
The following features are explicitly excluded from MVP v0.1:
- Real-time voice conversations.
- Voice cloning.
- Text-to-video generation.
- 3D avatars.
- Character animation.
- Multi-document personality extraction.
- Video-based character reconstruction.
- Cross-platform character portability.
- Third-party integrations.
- Fine-tuning custom LLMs.
- Advanced vector-based memory.
- Multi-agent orchestration.
- Social feeds.
- Character marketplaces.
- Payment processing.
- Native mobile applications.
Avoid spending development time on these features unless specifically requested.

Future voice architecture: Keep space for a voice_profile or external voice identifier, but do not make voice generation a dependency for v0.1.

6. Recommended Technology Stack
6.1 Frontend
Preferred: Next.js + TypeScript + Tailwind CSS

Responsibilities:
- Character creation page.
- Character editor.
- Character library.
- Chat interface.
- Image generation and editing controls.
- Loading and error states.
Use reusable UI components.

Avoid excessive animation or overly complex visual effects.
6.2 Backend
Preferred: Python + FastAPI

Responsibilities:
- Profile generation.
- Character CRUD operations.
- Profile refinement.
- LLM chat requests.
- Image generation and editing requests.
- Data persistence.
- API authentication with external providers.
- Validation and error handling.
6.3 Database
SQLite for local development.

Use a database access layer or ORM to allow future migration to PostgreSQL.

Recommended: SQLAlchemy and Alembic.
6.4 AI Integration
Implement the following service interfaces:
CharacterGenerationService
CharacterRefinementService
ChatService
ImageGenerationService
ImageEditingService
LLM and image model names must be configurable using environment variables.

Do not hardcode model names, prices, or provider secrets.

Suggested environment configuration:
LLM_PROVIDER=openai
LLM_MODEL=<configured-supported-model>

IMAGE_PROVIDER=ideogram
IMAGE_MODEL=<configured-supported-model>

OPENAI_API_KEY=
IDEOGRAM_API_KEY=

DATABASE_URL=sqlite:///./echoloom.db

MAX_PROFILE_INPUT_CHARS=5000
MAX_CHAT_CONTEXT_TOKENS=12000
The example values are configuration placeholders. The developer must check actual SDK interfaces and supported model identifiers before implementation.

If a recommended provider is unavailable or editing support is insufficient, explain the limitation and substitute an appropriate provider through the same interface.

7. Architecture
7.1 High-Level System
                EchoLoom Frontend
                       |
                       v
                 FastAPI Backend
                       |
         +-------------+-------------+
         |             |             |
         v             v             v
    Character       Chat API      Image API
    Generation       Service       Service
         |             |             |
         +-------------+-------------+
                       |
                       v
                Persistence Layer
                       |
                 SQLite + Files
7.2 AI Service Separation
Do not call third-party AI APIs directly from browser components.

All AI requests must go through the backend.

The backend controls:
- API keys.
- Prompt construction.
- Input validation.
- Cost limits.
- Error handling.
- Database operations.

8. Database Design
Implement at least the following entities.
8.1 Characters
Fields:
id
name
short_description
current_profile_version
current_image_id
created_at
updated_at
8.2 CharacterProfiles
id
character_id
version
profile_json
change_summary
created_at
Store approved profile revisions.
8.3 Conversations
id
character_id
created_at
updated_at
8.4 Messages
id
conversation_id
role
content
profile_version
created_at
Roles:
- user
- assistant
8.5 CharacterImages
id
character_id
parent_image_id
provider
model
prompt
file_path
version
created_at
The database design can be normalized further if justified.

Use UUIDs or equivalent stable identifiers.

9. Backend API Specification
Suggested REST endpoints:
Method	Endpoint	Purpose
POST	/api/characters/generate	Generate initial character profile
GET	/api/characters	List characters
GET	/api/characters/{id}	Retrieve character
PATCH	/api/characters/{id}	Update character fields
DELETE	/api/characters/{id}	Delete character
POST	/api/characters/{id}/refine	Propose AI-assisted profile edits
POST	/api/characters/{id}/refine/confirm	Confirm proposed changes
GET	/api/characters/{id}/versions	List profile revisions
POST	/api/characters/{id}/restore	Restore selected profile revision
POST	/api/characters/{id}/images/generate	Generate portrait
POST	/api/characters/{id}/images/edit	Edit existing portrait
GET	/api/characters/{id}/images	List portrait revisions
POST	/api/characters/{id}/images/{imageId}/select	Select current portrait
POST	/api/characters/{id}/conversations	Create conversation
GET	/api/conversations/{id}/messages	Retrieve messages
POST	/api/conversations/{id}/messages	Send message and generate replyThe developer may adjust endpoint naming, but every required operation must be supported.
AI-Assisted Profile Refinement
Use a preview/confirmation workflow.

A refinement request must not immediately overwrite the saved profile.

Return proposed changes first. Apply them only after user confirmation.
Image Editing
The first edited image must be saved as a candidate revision.

Selecting or accepting the image should be a separate operation.

10. Frontend Page Specifications
Page 1 — Character Library
Route: /characters

Display:
- Logo and navigation.
- "My Characters" heading.
- Grid of existing characters.
- "Create Character" button.
Empty state:
"Your characters are waiting to be created."

Page 2 — Create Character
Route: /characters/new

Display:
- Character description input.
- Example prompt.
- Create button.
- Loading indicator.
After successful generation, navigate to the Character Editor.
Page 3 — Character Editor
Route: /characters/{id}/edit

Two-column layout on desktop.

Left panel:
- Portrait.
- Generate Image button.
- Edit Image button.
- Image revision controls.
Right panel:
- Name.
- Description.
- Personality.
- Background.
- Appearance.
- Speech style.
- Save Changes.
- Refine with AI.
- Start Chat.
On mobile, use a stacked layout.
Page 4 — Character Chat
Route: /characters/{id}/chat

Display:
- Character portrait.
- Character name.
- Conversation messages.
- Message input.
- Send button.
- Edit Character action.
- Back to Library action.
The chat should visually distinguish user and character messages.

Do not allow the user to submit an empty message.

Automatically scroll to the latest response when appropriate.

11. UI/UX Guidelines
Design Direction
The product should feel:
- Friendly.
- Creative.
- Warm.
- Character-centered.
- Simple and approachable.
Avoid making it look like an enterprise dashboard.

Use rounded cards, clean typography, subtle colors, and generous spacing.

Suggested initial palette:
- Soft lavender.
- Light blue.
- Warm white.
- Dark navy text.
Support responsive layouts.
Core UX Principles
Minimal Friction
A user should be able to create a character without learning prompt engineering.
Edit Rather Than Restart
Character refinement must be easier than creating the character again.
Clear User Control
AI-proposed changes must be visible before acceptance.
Graceful Failure
If image generation fails, the character and text chat should remain usable.
Visible Persistence
Users should know that their character and changes have been saved.

12. AI Prompting Strategy
Character Generation
Use a dedicated prompt template instructing the model to:
- Extract explicit information from the user description.
- Organize it into the structured schema.
- Suggest reasonable missing attributes where appropriate.
- Preserve explicitly stated details.
- Avoid contradictory character traits.
- Return valid structured data.
Use schema-constrained outputs where supported.
Character Chat
The system or developer instruction should include:
- Character identity.
- Character background.
- Personality traits.
- Values.
- Speaking style.
- Behavior guidelines.
- Relevant conversation context.
The model should portray the fictional character naturally.

Avoid unnecessarily repeating profile descriptions in dialogue.

Keep the simulation consistent with the current character profile.

The application should remain transparent that the user is interacting with an AI character, not a real person.
Profile Refinement
Use a separate prompt template.

Input:
Current Character Profile
+
User Refinement Instruction
Output:
Proposed Field Changes
+
Short Explanation
Do not return an entirely unrelated new profile.

Treat user-provided descriptions and chat messages as content, not instructions to the backend to expose secrets or alter unrelated database records.

13. Cost and Safety Controls
The application must include basic API cost controls from the beginning.
Required Controls
- Maximum character description length.
- Configurable conversation context limit.
- Image generation request limits.
- Timeouts for external API calls.
- Reasonable retries with backoff.
- Prevention of repeated button submissions.
- Maximum accepted image file size.
- Error logging without exposing secrets.
- Environment-variable-based API credentials.
Set conservative default request budgets suitable for a local prototype.
Data Security
- Never expose API keys in frontend JavaScript.
- Never commit .env files.
- Validate all incoming API requests.
- Sanitize filenames and storage paths.
- Do not accept arbitrary filesystem paths from clients.
- Keep generated content and chat history associated with the correct character.
- Implement character deletion and cleanup of associated local data.
If deployed publicly, authentication, authorization, rate limiting, content moderation and multi-user data isolation must be implemented before inviting unrestricted users.

The local single-user MVP must not be represented as a production-secure multi-user service.

14. Development Plan
The implementation should be iterative.
Iteration 0 — Repository Inspection and Setup
Before coding:
1. Inspect the existing Echoloom_V2 repository.
2. Identify reusable components, existing structures and dependencies.
3. Preserve existing literature, schemas and research documents.
4. Determine the most appropriate location for the new application code.
5. Establish development commands.
6. Create or update .env.example.
7. Define database models and API contracts.
Do not reorganize unrelated project files unnecessarily.

Deliverable: Working frontend/backend project skeleton.
Iteration 1 — Character Generation
Implement:
- Create Character page.
- Character Profile schema.
- LLM integration.
- Profile generation endpoint.
- Database persistence.
- Character Editor.
Acceptance Criteria:
- User enters a character description.
- API generates a valid profile.
- Profile appears in the editor.
- User can manually edit and save it.
- Refreshing the page does not lose the character.
Iteration 2 — Character Chat
Implement:
- Chat endpoint.
- Conversation interface.
- Character-aware prompting.
- Conversation persistence.
- Loading/error states.
- Character Library.
Acceptance Criteria:
- User can create a character and start chatting.
- Responses incorporate the character profile.
- Conversation continues across multiple turns.
- Messages persist after refresh.
- User can reopen an existing character.
This is the first complete text-based MVP milestone.
Iteration 3 — Character Refinement
Implement:
- Natural-language profile refinement.
- Structured field patching.
- Modification preview.
- Confirm/reject workflow.
- Profile revision history.
- Restore previous version.
Acceptance Criteria:
- User can request a specific personality change.
- Unrelated fields remain unchanged.
- Chat history remains intact.
- Future responses use the new profile.
- User can restore an earlier profile.
Iteration 4 — Character Images
Implement:
- Image generation integration.
- Portrait display.
- Image storage.
- Natural-language image editing.
- Image revision history.
- Restore/select previous image.
Acceptance Criteria:
- User can generate a portrait from a saved profile.
- User can request an edit based on the current image.
- Previous images remain available.
- Failed image requests do not affect character or chat data.
- User can select which portrait is currently active.
Iteration 5 — Integration and Quality Assurance
Implement:
- End-to-end functional testing.
- Empty state handling.
- API failure handling.
- Input validation.
- UI polishing.
- Responsive layouts.
- Documentation.
Acceptance Criteria:

A new user can independently:
1. Create a character.
2. Review and edit its personality.
3. Generate a portrait.
4. Modify the portrait.
5. Start chatting.
6. Refine the character.
7. Return later and continue chatting.

15. Testing Requirements
Unit Tests
Test:
- Character schema validation.
- Profile update logic.
- Patch application.
- Profile version incrementing.
- Database CRUD operations.
- Invalid input handling.
Integration Tests
Test:
- Character generation API.
- Database persistence.
- Chat context construction.
- Image provider interface.
- Refinement confirmation.
- Image version creation.
Mock external AI services in automated tests.

Do not incur real API charges for normal unit test runs.
Manual End-to-End Test
Create an example character with:
- A distinctive appearance.
- Three personality traits.
- A background story.
- A specific speaking style.
Then verify:
- Profile generation.
- Profile editing.
- Chat response.
- AI-assisted profile refinement.
- Image creation.
- Image editing.
- Version restoration.
- Browser refresh persistence.
Critical Regression Scenario
Create a character, exchange several messages, modify one personality trait, and continue chatting.

Expected:
- Same character ID.
- Same conversation history.
- Updated personality for future messages.
- Unchanged previously saved messages.
- No unintended changes to portrait or backstory.

16. Non-Functional Requirements
Performance
- Show immediate feedback after the user starts an AI request.
- Do not freeze the UI during generation.
- Handle long-running image requests asynchronously where necessary.
- Avoid duplicate operations.
- Keep standard non-AI navigation responsive.
Reliability
- Save confirmed changes transactionally.
- Do not lose existing characters when external APIs fail.
- Handle invalid structured model outputs.
- Provide meaningful errors.
- Avoid silent failure.
Maintainability
- Modular service architecture.
- Centralized environment configuration.
- Type-safe data contracts.
- Reusable frontend components.
- Clear separation of UI, business logic and AI providers.
Observability
Record:
- AI provider and model.
- Request type.
- Latency.
- Success/failure.
- Token usage when available.
- Estimated request cost when feasible.
Do not log API keys or unnecessary personal conversation content.

17. Deliverables
The development AI should produce:
1. A working frontend application.
2. A working backend API.
3. SQLite database models and migrations.
4. Real LLM integration for character creation and chatting.
5. Real image generation and editing integration.
6. Character profile editor.
7. Character library.
8. Persistent chat history.
9. Profile and image versioning.
10. Basic automated tests.
11. .env.example.
12. Setup and run instructions.
13. Updated README or a dedicated MVP development README.
14. A list of completed functionality and known limitations.
The application must be runnable locally.

Do not describe a feature as completed unless it has been implemented and verified.

18. Development AI Instructions
The following instructions are intended for the coding assistant implementing this PRD.

Your role: Act as a senior full-stack engineer responsible for implementing EchoLoom MVP v0.1.
Before Writing Code
- Inspect the existing repository.
- Review existing architecture and dependencies.
- Preserve the project's literature and research assets.
- Identify reusable components.
- Check the current documentation for the APIs and SDKs you intend to use.
- Do not assume that a model name mentioned in earlier planning is a valid API identifier.
- Clearly identify any missing API keys or external requirements.
During Implementation
- Implement real functionality rather than static UI mockups.
- Work iteratively.
- Keep the application runnable after each major iteration.
- Use real backend persistence.
- Use provider abstractions.
- Avoid unnecessary complexity.
- Do not overwrite unrelated files.
- Do not introduce paid services beyond the selected providers without approval.
Implementation Priority
P0:
- Character creation.
- Structured profiles.
- Character editor.
- Character chat.
- Persistence.
- Character library.
- Profile refinement and revision history.
P1:
- Character image generation.
- Image editing.
- Image revisions.
- UI polish.
P2 / Deferred:
- Voice.
- Video.
- Long-term memory.
- Advanced persona extraction.
- Account system.
- Production deployment.
API Credentials
If API keys are unavailable:
- Implement the provider adapter and configuration.
- Use mocks for local tests.
- Clearly identify what cannot be verified without credentials.
- Do not fabricate successful live API results.
Completion Reporting
At the end of each iteration, report:
- What was implemented.
- Files changed.
- How to run it.
- What was tested.
- What remains incomplete.
- Whether real API calls were verified.
Important
Do not spend time implementing voice, video, complex personality extraction or multi-agent infrastructure during this MVP.

The immediate goal is a working, persistent, editable AI character creation and chat experience.

19. Final MVP Acceptance Checklist
- User can describe a character.
- AI generates a structured Character Profile.
- User can edit generated profile fields.
- User can save the character.
- Character remains available after refresh.
- User can chat with the character.
- Character responses use the saved profile.
- Chat history persists.
- User can refine the character using natural language.
- Proposed refinements can be previewed and approved.
- Earlier profile versions can be restored.
- User can generate a character portrait.
- User can edit an existing portrait.
- Earlier portrait versions remain available.
- User can reopen an existing character.
- External API failures are handled safely.
- API keys are not exposed.
- Basic tests pass.
- The project runs locally using documented commands.
MVP completion is defined by a successfully tested end-to-end user journey, not by the number of implemented features.

20. Post-MVP Roadmap
After v0.1 is functional and user-tested, future versions may include:

v0.2 — Voice Identity
- Generate voice candidates.
- Select and save a character voice.
- Convert chat responses to speech.
v0.3 — Voice Conversation
- Speech-to-text.
- Low-latency spoken interaction.
- Interruption handling.
- Voice consistency.
v0.4 — Advanced Personality Modeling
- Multi-document import.
- Evidence extraction.
- Structured personality reconstruction.
- Personality consistency evaluation.
- Character memory improvements.
v0.5 — Character Continuity & Portability
- Persistent cross-session memory.
- Model-independent character identity.
- Character export/import.
- Third-party integration API.
These features are future plans and must not delay MVP v0.1.

Final Product Principle
EchoLoom is not just an AI character generator.

It is a platform where users can create a character, shape its identity, interact with it, and continuously develop it over time.

The MVP should make this experience simple, intuitive, persistent and genuinely usable.




我建议你怎么交给编程 AI
直接把完整 PRD 发给它，并附上 Echoloom_V2 GitHub 仓库。

不过我建议不要第一句话就让它一次性完成全部功能。最好让它先分析仓库，并按照 PRD 的 Iteration 顺序实施和验证。

你可以额外附上这段启动指令：
Please use the attached EchoLoom MVP v0.1 PRD as the primary product specification.

First, inspect the existing GitHub repository and identify the current project structure, reusable components, and dependencies.

Then implement the MVP incrementally, starting with Iteration 0 and Iteration 1: Project Setup and Character Generation.

Please follow these requirements:
- Preserve the existing research and literature files.
- Build real, functional features rather than static mockups.
- Keep the architecture modular so AI providers can be replaced.
- Implement persistent data storage and proper error handling.
- Do not implement voice, video, or advanced personality extraction yet.
- Verify the actual API and SDK documentation before writing integrations.
- After each iteration, summarize completed work, tests, and remaining tasks.
Start by inspecting the repository and outlining the concrete file-level implementation plan. Then proceed with Iteration 0 and Iteration 1. Do not implement later iterations until the initial workflow is running and tested.




还有一个我特别建议注意的点
让编程 AI 优先做完整的 Create → Edit → Chat 闭环，而不是先花很多时间美化页面。

在第一版里，人物生成准确、编辑保存可靠、聊天能使用最新的人格设定，比 UI 动画更重要。

等这个闭环真正跑通后，再接生图和图片编辑 API。这样每完成一个 Iteration，你就有一个可以运行、可以测试的产品，而不必等所有功能写完才能发现问题。