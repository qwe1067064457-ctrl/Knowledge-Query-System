---
name: "file-management"
description: "Manages file modifications, deletions, and additions, including indexing, AI veto power, and a three-step AI modification process. Invoke when handling file operations or AI-driven content changes."
---

# File Management Agent

This skill is designed to manage file operations within the knowledge base, ensuring data consistency and intelligent handling of content changes.

## Functionality

### 1. File Modification (Incremental Indexing)
- When a user saves or exits a file, or an AI notifies of a file modification, the task enters a message queue.
- Duplicate tasks are removed from the queue.
- A new index is built for the modified file.
- The old index for the file is deleted.

### 2. File Deletion
- When a user deletes a file, or an AI notifies of a file deletion, the task enters a message queue.
- Duplicate tasks are removed from the queue.
- The corresponding index is deleted.

### 3. File Addition
- When a user adds a new file, or an AI notifies of a file addition, the task enters a message queue.
- Duplicate tasks are removed from the queue.
- A new index is created for the added file.

### 4. Agent "Veto Power"
- Before pushing a modification task to the message queue, the agent compares the semantic hash or text difference of the file content.
- If the difference is minimal (below a defined threshold), the agent intercepts the task, preventing it from entering the queue and avoiding unnecessary index rebuilding. This saves computational resources.

### 5. AI Modification "Three-Step Process"
- When an AI decides to modify the knowledge base, it does not directly write to the file.
- **Generate Diff**: The AI outputs the modified content, and the system calculates the differences (added/deleted lines).
- **Create "Todo Task"**: A notification pops up in the user interface, e.g., "AI suggests updating the attendance section in the 'Employee Handbook'".
- **User Decision**: The user can choose to:
    - **Accept**: The system performs the write operation, and the subsequent process is the same as "User Save".
    - **Reject**: The modification is discarded, and the file remains unchanged.
    - **Edit**: The user manually fine-tunes the changes in a diff interface before accepting.

## Interface Interaction Suggestions

- **Change Review Panel**:
    - Left side: Original content (gray background).
    - Right side: AI modified content (green highlight for additions, red highlight for deletions).
    - Bottom buttons: [Reject] [Accept and Save].

## Summary

- **User Changes**: Take effect immediately (trust user).
- **AI Changes**: Proposed changes require user approval.
- **Underlying Unification**: Regardless of who makes the change, once it's committed, it triggers the same MQ message and follows the same indexing process.
