# Development Process

## Communication

Development was coordinated primarily through Discord, where the team held regular working sessions to discuss architecture, implementation details, debugging, and testing.

Outside of scheduled sessions, communication was maintained through WhatsApp for quick discussions and coordination.

## Planning

GitHub Issues were used to track remaining work, implementation progress, testing tasks, and bug fixes throughout the project.

The team followed an incremental development process:

1. Registration protocol integration
2. Blockchain data structures
3. Transaction propagation
4. Mempool implementation
5. Mining functionality
6. Block propagation
7. Chain synchronization
8. Testing and stabilization

## Development Strategy

Rather than assigning strict ownership of subsystems, the team adopted a collaborative approach.

Initially, each member developed their own implementation while adhering to an agreed-upon architecture. This allowed multiple approaches to be explored in parallel.

After evaluating the individual implementations, the strongest components were merged into a synchronized repository. From that point onward, most development, debugging, testing, and refinement were performed collaboratively.

## Quality Assurance

Testing focused on validating both individual components and full-system behavior.

The team repeatedly tested:

* Registration and peer discovery
* Transaction propagation
* Mining correctness
* Block validation
* Chain synchronization
* Fork handling
* Server interaction

Issues discovered during testing were tracked and resolved through GitHub Issues and collaborative debugging sessions.
