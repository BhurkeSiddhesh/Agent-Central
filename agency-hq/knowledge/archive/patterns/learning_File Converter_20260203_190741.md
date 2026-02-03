# Learning from File Converter

- **Real-time UX**: Implementing Server-Sent Events (SSE) requires wrapping blocking calls in `run_in_threadpool` (in FastAPI) to avoid blocking the event loop and ensure smooth UI updates.
- **Visual Feedback**: Pulsing animations and gradient transitions significantly improve the perceived quality of asynchronous file operations.
- **Agency Configuration**: Using descriptive natural language in `agency.yaml` helps in better role definition and task alignment for specialized agents.
- **Git Hygiene**: Regular branch sweeping and testing loops (Jules Watchdog) are critical for maintaining code integrity in collaborative/agentic environments.