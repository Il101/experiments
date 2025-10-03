# Preset Management UI

<cite>
**Referenced Files in This Document**
- [Presets.tsx](file://frontend/src/pages/Presets.tsx)
- [PresetEditForm.tsx](file://frontend/src/components/PresetEditForm.tsx)
- [usePresets.ts](file://frontend/src/hooks/usePresets.ts)
- [presets.py](file://breakout_bot/api/routers/presets.py)
- [breakout_v1.json](file://breakout_bot/config/presets/breakout_v1.json)
- [endpoints.ts](file://frontend/src/api/endpoints.ts)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Dependency Analysis](#dependency-analysis)
7. [Performance Considerations](#performance-considerations)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Conclusion](#conclusion)

## Introduction
The Preset Management interface enables users to manage trading strategy configurations through a comprehensive UI for viewing, selecting, editing, and saving presets. The system integrates frontend components with backend API endpoints to provide real-time synchronization of configuration changes across clients. This documentation details the implementation of the Presets page, the PresetEditForm component, and the underlying data flow between UI elements and server-side storage.

## Project Structure
The preset management functionality spans both frontend and backend components within the repository. Frontend code resides in the `frontend/src` directory with dedicated files for pages, components, hooks, and API endpoints. Backend implementation is located in the `breakout_bot/api/routers` module, with configuration files stored in `breakout_bot/config/presets`.

```mermaid
graph TB
subgraph "Frontend"
P[Presets.tsx]
F[PresetEditForm.tsx]
H[usePresets.ts]
E[endpoints.ts]
end
subgraph "Backend"
R[presets.py]
C[config/presets/*.json]
end
P --> H
F --> H
H --> E
E --> R
R --> C
```

**Diagram sources**
- [Presets.tsx](file://frontend/src/pages/Presets.tsx)
- [PresetEditForm.tsx](file://frontend/src/components/PresetEditForm.tsx)
- [usePresets.ts](file://frontend/src/hooks/usePresets.ts)
- [endpoints.ts](file://frontend/src/api/endpoints.ts)
- [presets.py](file://breakout_bot/api/routers/presets.py)

**Section sources**
- [Presets.tsx](file://frontend/src/pages/Presets.tsx)
- [PresetEditForm.tsx](file://frontend/src/components/PresetEditForm.tsx)
- [presets.py](file://breakout_bot/api/routers/presets.py)

## Core Components
The preset management system consists of three primary components: the Presets page for displaying available configurations, the PresetEditForm for inline parameter editing, and the usePresets hook for managing CRUD operations against the API. These components work together to provide a seamless experience for modifying trading strategy parameters including scan filters, signal thresholds, risk limits, and position sizing rules.

**Section sources**
- [Presets.tsx](file://frontend/src/pages/Presets.tsx#L1-L140)
- [PresetEditForm.tsx](file://frontend/src/components/PresetEditForm.tsx#L1-L191)
- [usePresets.ts](file://frontend/src/hooks/usePresets.ts#L1-L48)

## Architecture Overview
The preset management architecture follows a client-server pattern with React Query handling state management on the frontend and FastAPI providing RESTful endpoints on the backend. Configuration data is persisted as JSON files in the filesystem, accessed through standardized API routes that support listing, retrieving, and updating preset configurations.

```mermaid
sequenceDiagram
participant User as "User"
participant UI as "Presets UI"
participant Hook as "usePresets"
participant API as "API Client"
participant Server as "FastAPI Server"
participant FS as "File System"
User->>UI : View Presets Page
UI->>Hook : usePresets()
Hook->>API : GET /api/presets/
API->>Server : Request
Server->>FS : Read all .json files
FS-->>Server : Preset data
Server-->>API : Response
API-->>Hook : Preset summaries
Hook-->>UI : Update state
UI-->>User : Display preset list
User->>UI : Click "View Config"
UI->>Hook : usePreset(name)
Hook->>API : GET /api/presets/{name}
API->>Server : Request
Server->>FS : Read specific .json file
FS-->>Server : Configuration data
Server-->>API : Response
API-->>Hook : Full config
Hook-->>UI : Update modal
UI-->>User : Show editable form
User->>UI : Modify parameters and Save
UI->>Hook : useUpdatePreset()
Hook->>API : PUT /api/presets/{name}
API->>Server : Send updated config
Server->>FS : Write to .json file
FS-->>Server : Success
Server-->>API : Confirmation
API-->>Hook : Success response
Hook->>Hook : Invalidate queries
Hook-->>UI : Close modal
```

**Diagram sources**
- [Presets.tsx](file://frontend/src/pages/Presets.tsx#L1-L140)
- [usePresets.ts](file://frontend/src/hooks/usePresets.ts#L1-L48)
- [presets.py](file://breakout_bot/api/routers/presets.py#L1-L107)

## Detailed Component Analysis

### Presets Page Analysis
The Presets page displays a table of available trading strategy configurations with metadata including name, description, risk level, and strategy type. Users can select any preset to view and edit its full configuration through a modal interface.

```mermaid
flowchart TD
Start([Page Load]) --> FetchPresets["usePresets() hook fetches\npreset summaries from /api/presets/"]
FetchPresets --> DisplayTable["Render table with columns:\n• Name\n• Description\n• Strategy Type (Badge)\n• Risk per Trade (%)\n• Max Positions (Badge)"]
DisplayTable --> WaitForAction["Wait for user action"]
WaitForAction --> CheckSelection{Selected preset?}
CheckSelection --> |Yes| FetchConfig["usePreset() hook fetches\nfull configuration from\n/api/presets/{name}"]
CheckSelection --> |No| WaitForAction
FetchConfig --> ShowModal["Display PresetEditForm\nin modal dialog"]
ShowModal --> HandleSave["On Save: useUpdatePreset()\nmutation sends PUT request"]
HandleSave --> ValidateResponse{Success?}
ValidateResponse --> |Yes| RefreshData["Invalidate cache,\nclose modal"]
ValidateResponse --> |No| ShowError["Display error message"]
RefreshData --> DisplayTable
ShowError --> ShowModal
```

**Diagram sources**
- [Presets.tsx](file://frontend/src/pages/Presets.tsx#L1-L140)

**Section sources**
- [Presets.tsx](file://frontend/src/pages/Presets.tsx#L1-L140)

### PresetEditForm Component Analysis
The PresetEditForm component provides an interactive interface for editing nested configuration parameters. It supports recursive rendering of complex objects and includes validation mechanisms to prevent invalid configurations.

```mermaid
classDiagram
class PresetEditForm {
+preset : PresetConfig | null
+onSave : (config : Record<string,any>) => void
+onCancel : () => void
+loading : boolean
-config : Record<string,any>
-errors : Record<string,string>
+handleInputChange(path[], value)
+validateConfig() : boolean
+handleSave()
+renderNestedForm(obj, path) : ReactNode
}
class PresetConfig {
+name : string
+config : Record<string,any>
}
PresetEditForm --> PresetConfig : uses
PresetEditForm ..> Alert : displays
PresetEditForm ..> Form : renders
PresetEditForm ..> Button : controls
```

**Diagram sources**
- [PresetEditForm.tsx](file://frontend/src/components/PresetEditForm.tsx#L1-L191)

**Section sources**
- [PresetEditForm.tsx](file://frontend/src/components/PresetEditForm.tsx#L1-L191)

### usePresets Hook Analysis
The usePresets hook encapsulates all API interactions for preset management, leveraging React Query for efficient data fetching, caching, and mutation handling. It ensures synchronization across clients by invalidating relevant queries after successful updates.

```mermaid
flowchart LR
A[usePresets] --> B[Query: getPresets]
A --> C[Query: getPreset]
A --> D[Mutation: updatePreset]
B --> E["GET /api/presets/\nReturns PresetSummary[]"]
C --> F["GET /api/presets/{name}\nReturns PresetConfig"]
D --> G["PUT /api/presets/{name}\nUpdates configuration"]
G --> H["On Success:\n• Invalidate getPreset query\n• Invalidate getPresets query"]
style A fill:#f9f,stroke:#333
style B fill:#bbf,stroke:#333
style C fill:#bbf,stroke:#333
style D fill:#f96,stroke:#333
```

**Diagram sources**
- [usePresets.ts](file://frontend/src/hooks/usePresets.ts#L1-L48)
- [endpoints.ts](file://frontend/src/api/endpoints.ts#L83-L120)

**Section sources**
- [usePresets.ts](file://frontend/src/hooks/usePresets.ts#L1-L48)

## Dependency Analysis
The preset management system has well-defined dependencies between frontend and backend components. The UI layers depend on hooks for data access, which in turn rely on API endpoints that communicate with server-side routers.

```mermaid
graph TD
A[Presets.tsx] --> B[usePresets.ts]
C[PresetEditForm.tsx] --> B
B --> D[endpoints.ts]
D --> E[presets.py]
E --> F[config/presets/*.json]
style A fill:#aef,stroke:#333
style C fill:#aef,stroke:#333
style B fill:#fea,stroke:#333
style D fill:#fea,stroke:#333
style E fill:#eaf,stroke:#333
style F fill:#afa,stroke:#333
```

**Diagram sources**
- [Presets.tsx](file://frontend/src/pages/Presets.tsx)
- [PresetEditForm.tsx](file://frontend/src/components/PresetEditForm.tsx)
- [usePresets.ts](file://frontend/src/hooks/usePresets.ts)
- [endpoints.ts](file://frontend/src/api/endpoints.ts)
- [presets.py](file://breakout_bot/api/routers/presets.py)

**Section sources**
- [usePresets.ts](file://frontend/src/hooks/usePresets.ts#L1-L48)
- [endpoints.ts](file://frontend/src/api/endpoints.ts#L83-L120)
- [presets.py](file://breakout_bot/api/routers/presets.py#L1-L107)

## Performance Considerations
The preset management system implements several performance optimizations:
- Client-side caching with 5-minute stale time for preset data
- Selective query invalidation to minimize unnecessary refetching
- Efficient JSON file I/O operations on the server side
- Lazy loading of full preset configurations only when needed

These optimizations ensure responsive UI performance while maintaining data consistency across multiple clients.

## Troubleshooting Guide
Common issues in the preset management system typically involve configuration validation failures or file system access problems. The system provides user feedback through form validation messages and handles errors gracefully at both client and server levels.

**Section sources**
- [PresetEditForm.tsx](file://frontend/src/components/PresetEditForm.tsx#L54-L128)
- [presets.py](file://breakout_bot/api/routers/presets.py#L25-L107)

## Conclusion
The Preset Management UI provides a robust interface for configuring trading strategies with proper validation, error handling, and real-time synchronization. By aligning UI fields with the underlying JSON schema used in breakout_bot/config/presets/*.json files, the system ensures consistency between frontend inputs and backend expectations. While the current implementation does not explicitly address concurrency concerns for multiple users editing the same preset simultaneously, the atomic file write operations provide basic protection against data corruption.