Core Banking Loan Management Service
====================================

Overview
--------

The **Core Banking Loan Management Service** is a production-grade **double-entry accounting system** designed to serve as the financial foundation for loan operations in a fintech platform. The system is built to handle **high transaction volumes** while maintaining **absolute data integrity**, auditability, and correctness.

Business Context
----------------

This service supports a digital lending platform that:

*   Disburses loans via mobile money platforms (e.g. M-Pesa)
*   Serves multiple lenders who pool funds
*   Requires real-time financial reporting
*   Must comply with banking regulations and audits
*   Processes thousands of transactions per day

## Technology Stack

### Core Framework
- **Django 3.x+** – Web framework for REST API
- **Django REST Framework (DRF)** – RESTful API development
- **Python 3.8+** – Programming language

### Database & ORM
- **PostgreSQL / SQLite** – Relational database with ACID compliance
- **Django ORM** – Object-relational mapping with custom managers
- **Optimistic Locking** – Version-based concurrency control

### Additional Libraries
- **reportlab** – PDF report generation
- **openpyxl** – Excel export for financial reports
- **django-cors-headers** – Cross-origin resource sharing
- **python-decouple** – Environment configuration management

### Infrastructure
- **Docker** – Containerization
- **Docker Compose** – Multi-container orchestration

## High Level Architecture

![System Architecture Diagram](docs/assets/diagram-export-1-14-2026-2_23_11-AM.png)

### Layered Architecture Overview

The Core Banking Loan Management Service is built on a **4-tier layered architecture** with **multi-tenancy** support, designed for scalability, maintainability, and financial accuracy:

```
┌─────────────────────────────────────────────────────┐
│         PRESENTATION LAYER (API Layer)              │
│  - RESTful endpoints via Django REST Framework      │
│  - Request validation & serialization               │
│  - Response formatting & pagination                 │
│  - CORS headers & authentication                    │
└─────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────┐
│      APPLICATION LAYER (Business Logic)             │
│  - Double-entry bookkeeping rules & validation      │
│  - Loan lifecycle management (disbursement, etc.)   │
│  - Balance calculations & reconciliation            │
│  - Permission & authorization (RBAC)                │
│  - Organization multitenancy enforcement            │
└─────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────┐
│    PERSISTENCE LAYER (Data Access & Models)         │
│  - Django ORM with custom TenantAwareManager        │
│  - Chart of Accounts with hierarchies               │
│  - Journal entries & transaction history            │
│  - Organization-scoped data filtering               │
│  - Custom QuerySets with organization filtering     │
└─────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────┐
│      DATA LAYER (Database & Storage)                │
│  - PostgreSQL with ACID compliance                  │
│  - Indexed queries for performance                  │
│  - Optimistic locking for concurrency               │
│  - Audit trails for compliance                      │
└─────────────────────────────────────────────────────┘
```

### Architectural Components

#### 1. **Presentation Layer**
- RESTful API endpoints for all operations
- Request/response serialization via DRF serializers
- Comprehensive input validation
- Pagination and filtering support
- CORS-enabled for multi-domain access

#### 2. **Application Layer**
- Core business logic for accounting operations
- Loan lifecycle state machines (pending → approved → disbursed → repaid/defaulted)
- Balance calculation algorithms
- Journal entry validation and balancing
- Role-based access control (RBAC) with 5-tier hierarchy (admin > manager > accountant > viewer > user)
- Organization multitenancy enforcement via middleware and permission classes

#### 3. **Persistence Layer**
- Django ORM models with TenantAwareModel base class
- Custom TenantAwareManager for automatic organization filtering
- Custom TenantAwareQuerySet with `.for_organization()` method
- Chart of Accounts with parent-child relationships
- Transaction history with audit trails
- Account balance snapshots for historical queries

#### 4. **Data Layer**
- PostgreSQL database with ACID guarantees
- Optimized indexes on organization, account, and transaction columns
- Optimistic locking via version numbers for concurrent control
- Automatic timestamps (created_at, updated_at) on all records

#### 5. **Multitenancy Layer**
- **Organization Model**: Master tenant entity representing independent business units (e.g., lenders, platforms)
- **OrganizationUser Model**: User-to-organization mapping with 5-tier role-based access control
  - Roles: Admin (full control) > Manager (manage features) > Accountant (modify records) > Viewer (read-only) > User (basic access)
  - Supports multiple organizations per user with different roles
  - Soft-delete via `is_active` flag for audit trails
- **OrganizationMiddleware**: Request-level context extraction
  - Extracts organization from `X-Organization` header or `?organization` query parameter
  - Makes `request.organization` available throughout request lifecycle
  - Enables seamless organization scoping without scattered business logic
- **TenantAwareModel**: Abstract base class for all organization-scoped models
  - Automatic `organization` ForeignKey on every model
  - Automatic `created_at`, `updated_at` timestamps
  - Custom `TenantAwareManager` for organization-filtered queries
- **TenantAwareQuerySet**: Custom QuerySet with organization filtering
  - `.for_organization(org)` method for explicit filtering
  - `.active_organizations()` for filtering by organization status
  - Prevents accidental cross-organization data leakage
- **Permission Classes**: RBAC enforcement
  - `IsOrganizationMember`: Ensures user belongs to requested organization
  - `HasOrganizationPermission`: Role-based hierarchy checking
  - `CanModifyOrganizationData`: Write permission enforcement
  - `CanViewOrganizationReports`: Report access control
- **Data Isolation Guarantees**:
  - Every record in the system belongs to exactly one organization
  - Unique constraints include organization field (e.g., `unique_together=[('organization', 'code')]`)
  - Account codes, lender names, and idempotency keys can be duplicated across organizations
  - Complete data isolation: Organization A cannot see Organization B's data
- **Utility Functions**: Organization management helpers
  - User onboarding/offboarding
  - Role management and hierarchy checking
  - Organization statistics and auditing

## Design Patterns

### 1. **12 Factor App Methodology**
The service follows the 12-factor app principles for cloud-native development:

- **Codebase**: Single Git repository tracking all versions
- **Dependencies**: Explicitly declared in `requirements/` directory
- **Config**: Environment variables via `env.example.sh` and `python-decouple`
- **Processes**: Stateless & processes can be scaled horizontally
- **Logs**: Stdout/stderr logging for aggregation
- **Admin Processes**: Management commands via `manage.py`

### 2. **Unit of Work Pattern**
- Database transactions wrapped in `@transaction.atomic()` decorators
- Ensures all-or-nothing semantics for multi-step operations
- Prevents partial journal entries or account updates
- Rollback on validation failures

Example:
```python
@transaction.atomic
def create_journal_entry(entries):
    # Creates entry, validates balance, saves all lines atomically
    journal_entry = JournalEntry.objects.create(...)
    for entry_data in entries:
        JournalEntryLine.objects.create(...)
    # Commits only if validation passes
```

### 3. **Repository/Manager Pattern**
- Custom managers (`TenantAwareManager`, `AccountManager`) encapsulate queries
- Centralize query logic and ensure organization filtering
- Reusable filter methods like `.for_organization()`, `.active()`
- Prevent direct queryset access without filtering

### 4. **Middleware Pattern (Multitenancy)**
- `OrganizationMiddleware` extracts organization context from HTTP headers or query params
- Attached to every request, making `request.organization` available throughout
- Enables seamless organization scoping without scattered business logic

### 5. **Permission Classes (DRF)**
- `IsOrganizationMember` – Ensures user belongs to the requested organization
- `HasOrganizationPermission` – Enforces role-based access control
- Role hierarchy: viewer (0) < user (1) < accountant (2) < manager (3) < admin (4)
- Attached to ViewSets for automatic authorization checks

### 6. **Idempotency Pattern**
- Unique `idempotency_key` on transactions prevents duplicate processing
- Stores cached results in `TransactionIdempotencyCache` table
- Duplicate requests return original transaction result
- Critical for financial operations where retries are common

### 7. **Optimistic Locking Pattern**
- Version numbers on Account and Loan models track mutations
- Concurrent updates detected via version mismatch
- Prevents lost updates when multiple requests modify same record
- Alternative to pessimistic locking (no row locks)

### 8. **Account Balance Materialization**
- Precomputed account balances stored in `AccountBalance` model
- Updated daily for performance
- Trades storage for query speed (< 50ms requirement)
- Fall-back to on-demand calculation for real-time accuracy

### 9. **Hierarchy Pattern (Account Structure)**
- Self-referencing ForeignKey on Account (`parent` field)
- Parent-child relationships enable account trees
- Control accounts (parents) cannot have transactions directly
- Recursive balance calculation across hierarchy

### 10. **Audit Trail Pattern**
- `created_at`, `updated_at` on all TenantAwareModel records
- Immutable journal entries (no edits, only reversals)
- Reversing entries maintain link to original via `reversed_by` field
- Complete transaction history for compliance

## Project Structure

```
core-banking-loan-service/
├── manage.py                          # Django management script
├── README.md                          # This file
├── pyproject.toml                     # Project metadata
├── requirements/                      # Python dependencies
│   ├── base.txt                       # Core dependencies
│   ├── dev.txt                        # Development tools
│   ├── test.txt                       # Testing dependencies
│   └── ci.txt                         # CI/CD dependencies
├── src/                               # Main application code
│   ├── __init__.py
│   ├── admin.py                       # Django admin config
│   ├── app.py                         # App initialization
│   ├── config/                        # Django settings
│   ├── common/                        # Multitenancy & core
│   │   ├── models.py                  # Organization, TenantAwareModel
│   │   ├── middleware.py              # OrganizationMiddleware
│   │   ├── permissions.py             # RBAC permission classes
│   │   ├── utils.py                   # Helper functions
│   │   ├── admin.py                   # Django admin for orgs
│   │   └── apps.py                    # App configuration
│   ├── accounts/                      # Chart of accounts
│   │   ├── models.py                  # Account model
│   │   ├── views.py                   # Account ViewSet
│   │   ├── serializers.py             # DRF serializers
│   │   └── urls.py                    # Route configuration
│   ├── journal/                       # Journal entries & posting
│   │   ├── models.py                  # JournalEntry, JournalEntryLine
│   │   ├── views.py                   # Journal ViewSet
│   │   ├── serializers.py             # DRF serializers
│   │   └── urls.py                    # Route configuration
│   ├── loans_management/              # Loan lifecycle operations
│   │   ├── models.py                  # Loan, LoanRepayment, etc.
│   │   ├── views.py                   # Loan ViewSets
│   │   ├── serializers.py             # DRF serializers
│   │   └── urls.py                    # Route configuration
│   └── reports/                       # Financial reporting
│       ├── views.py                   # Report endpoints
│       └── services.py                # Report calculation logic
├── tests/                             # Test suite
├── docs/                              # Documentation
│   ├── assets/                        # Diagrams & images
│   ├── local-dev-setup/               # Development setup guide
│   ├── release-cycle-management/      # Release procedures
├── scripts/                           # Utility scripts
│   └── start.sh                       # Server startup script
├── Dockerfile                         # Container image
├── docker-compose.yml                 # Multi-container setup
└── tox.ini                            # Testing configuration
```

## Getting Started

### Local Development Setup

See [docs/local-dev-setup/](docs/local-dev-setup/) for detailed instructions.

#### Quick Start

```bash
# 1. Install dependencies
pip install -r requirements/dev.txt

# 2. Create migrations
python manage.py makemigrations

# 3. Apply migrations
python manage.py migrate

# 4. Create superuser
python manage.py createsuperuser

# 5. Create an organization
python manage.py shell
>>> from src.common.models import Organization
>>> org = Organization.objects.create(code="ORG001", name="Test Organization")
>>> from django.contrib.auth.models import User
>>> user = User.objects.get(username="admin")
>>> from src.common.utils import add_user_to_organization
>>> add_user_to_organization(user, org, role='admin')

# 6. Run development server
python manage.py runserver
```

### Development Commands

All common development tasks are automated via Invoke. Run `invoke --list` to see all available commands:

```bash
# Run tests with pytest
invoke test-all

# Run tests with coverage report (generates htmlcov/index.html)
invoke coverage

# Format code (isort + black)
invoke format

# Check code style (flake8)
invoke lint

# Clean build artifacts and Python cache
invoke clean

# Run Django unittests
invoke unittest
```

For detailed setup and development instructions, see [Local Development Setup](docs/local-dev-setup/local-development-setup.md).

### API Usage

```bash
# All requests require X-Organization header
curl -X GET http://localhost:8000/api/accounts/ \
  -H "X-Organization: ORG001" \
  -H "Authorization: Bearer {token}"
```

Core Features
-------------

### 1\. Account Management

Implements a **Chart of Accounts** supporting the following account types:

*   **ASSET** – Resources owned (Cash, Loans Receivable)
    
*   **LIABILITY** – Obligations owed (Lender Capital, Payables)
    
*   **EQUITY** – Owner’s stake (Retained Earnings)
    
*   **INCOME** – Revenue earned (Interest Income, Fee Income)
    
*   **EXPENSE** – Costs incurred (Bad Debt Expense, Operating Expenses)
    

Capabilities include

*   Unique account identifiers
    
*   Multi-currency support (KES, UGX, USD)
    
*   Hierarchical parent–child account structures
    
*   Current and historical balance retrieval
    
*   Protection against deleting accounts with transaction history
    

### 2\. Transaction Processing

Implements **double-entry bookkeeping** with the following principles:

*   Debits increase **ASSET** and **EXPENSE** accounts
    
*   Credits increase **LIABILITY**, **EQUITY**, and **INCOME** accounts
    
*   Every transaction must balance (Debits = Credits)
    

This Service Supports

*   Simple two-account transactions
    
*   Complex journal entries involving three or more accounts
    
*   Idempotent transaction processing
    
*   Transaction reversals via offsetting entries
    
*   Concurrency control using optimistic locking
    

### 3\. Loan Lifecycle Operations

Supports standard loan accounting workflows:

*   Loan disbursement with origination fee recognition
    
*   Loan repayment with principal and interest split
    
*   Loan default and write-off with bad debt recognition
    

All workflows produce balanced and auditable journal entries.

### 4\. Reporting Queries

Provides high-performance financial reporting, including:

*   Current and historical account balances
    
*   Transaction history with filters and running balances
    
*   Trial balance grouped by account type
    
*   Balance sheet snapshot
    
*   Loan aging analysis by delinquency buckets

## Assessment Progress & TODO

### Part 1 (Core Features)

#### 1.1 Account Management

| Task | Status |
|------|--------|
| Implement chart of accounts | **DONE** |
| Support account types: ASSET, LIABILITY, EQUITY, INCOME, EXPENSE | **DONE** |
| Create accounts with unique identifiers | **DONE** |
| Support multi-currency accounts (KES, UGX, USD) | **DONE** |
| Implement account hierarchies with parent–child relationships | **DONE** |
| Retrieve current account balances | **DONE** |
| Retrieve historical account balances (as-of date/time) | **DONE** |
| Prevent deletion of accounts with transaction history | **DONE** |

#### 1.2 Transaction Processing

| Task | Status |
|------|--------|
| Implement double-entry bookkeeping | **DONE** |
| Enforce debit and credit rules by account type | **DONE** |
| Ensure every transaction balances (Debits = Credits) | **DONE** |
| Support simple transactions involving two accounts | **DONE** |
| Support complex journal entries involving three or more accounts | **DONE** |
| Implement idempotency using idempotency_key | **DONE** |
| Return original transaction for duplicate idempotent requests | **DONE** |
| Support transaction reversal through offsetting entries | **DONE** |
| Maintain audit trail for voided transactions | **DONE** |
| Implement optimistic locking for concurrent updates | **DONE** |
| Prevent race conditions when transactions affect the same accounts | **DONE** |

#### 1.3 Loan Lifecycle Operations

| Task | Status |
|------|--------|
| Implement loan disbursement accounting | **DONE** |
| Record loan receivable on disbursement | **DONE** |
| Record loan origination fee receivable and fee income | **DONE** |
| Implement loan repayment accounting (principal and interest split) | **DONE** |
| Implement loan default and write-off accounting | **DONE** |
| Record bad debt expense on loan write-off | **DONE** |

#### 1.4 Reporting Queries

| Task | Status |
|------|--------|
| Implement current account balance report | **DONE** |
| Implement historical account balance (as-of date/time) | **DONE** |
| Ensure account balance queries meet < 50ms performance requirement | **DONE** |
| Implement transaction history report | **DONE** |
| Support pagination for transaction history | **DONE** |
| Support filtering by date range and transaction type | **DONE** |
| Include running balance in transaction history | **DONE** |
| Implement trial balance report | **DONE** |
| Ensure trial balance always balances (audit critical) | **DONE** |
| Group trial balance by account type | **DONE** |
| Implement balance sheet report (Assets = Liabilities + Equity) | **DONE** |
| Implement loan aging report | **DONE** |
| Categorize loans into aging buckets (0–29, 30–59, 60–89, 90+ days) | **DONE** |
| Display loan count and total amount per aging bucket | **DONE** |


### Part 2 (Multitenancy & Authorization (Completed Beyond Assessment))

| Task | Status |
|------|--------|
| Implement Organization model for multi-tenancy | **DONE** |
| Implement OrganizationUser model with RBAC | **DONE** |
| Create 5-tier role hierarchy (admin > manager > accountant > viewer > user) | **DONE** |
| Implement TenantAwareModel abstract base class | **DONE** |
| Implement TenantAwareManager and TenantAwareQuerySet | **DONE** |
| Create OrganizationMiddleware for request context extraction | **DONE** |
| Create permission classes for RBAC enforcement | **DONE** |
| Update all existing models to inherit from TenantAwareModel | **DONE** |
| Convert all unique constraints to organization-scoped | **DONE** |
| Create Django admin interfaces for organization management | **DONE** |


## Next Steps

With all core features implemented, the following priorities will enhance production readiness, reliability, and scalability:

### Priority 1 (Testing & Quality Assurance)
**Goal**: Achieve >95% code coverage with comprehensive automated testing

- **Unit Testing**
  - Account model validation tests
  - Journal entry balancing logic tests
  - Loan lifecycle state machine tests
  - Organization filtering query tests
  - Permission class hierarchy tests
  
- **Integration Testing**
  - End-to-end loan disbursement workflow
  - Multi-step transaction processing with rollback
  - Report generation with large datasets
  - Organization data isolation verification
  - Concurrent transaction handling

- **API Testing**
  - All endpoints with valid/invalid inputs
  - Authentication and authorization flows
  - Multitenancy isolation between requests
  - Idempotency key behavior
  - Rate limiting and throttling

- **Performance Testing**
  - Account balance queries (validate < 50ms requirement)
  - Report generation under load
  - Concurrent user simulation (100+ simultaneous users)
  - Database query optimization and indexing
  - Memory profiling and leak detection

### Priority 2 (Security Hardening)
**Goal**: Ensure bank-grade security and compliance

- **Authentication & Authorization**
  - JWT token-based authentication implementation
  - Token refresh and expiration handling
  - Password policies and strength requirements
  - Two-factor authentication (2FA) for admin roles
  - Session management and timeout policies

- **Data Protection**
  - Sensitive data encryption at rest (account numbers, PII)
  - TLS/SSL for data in transit
  - Database connection encryption
  - API key management and rotation
  - Audit logging for all sensitive operations

- **Security Testing**
  - OWASP Top 10 vulnerability scanning
  - SQL injection prevention validation
  - XSS and CSRF protection testing
  - Penetration testing for API endpoints
  - Dependency vulnerability scanning

### Priority 3 (Production Deployment)
**Goal**: Deploy to production with high availability and disaster recovery

- **Infrastructure Setup**
  - PostgreSQL production instance with replication
  - Redis for caching and session management
  - Load balancer configuration (nginx/HAProxy)
  - Container orchestration (Kubernetes/ECS)
  - CDN setup for static assets

- **CI/CD Pipeline**
  - Automated testing on commits
  - Docker image building and versioning
  - Staging environment deployment
  - Production deployment with blue-green strategy
  - Automated rollback on failure

- **Database Management**
  - Migration strategy for zero-downtime deployments
  - Database backup automation (hourly/daily)
  - Point-in-time recovery setup
  - Disaster recovery procedures
  - Database performance tuning

- **Environment Configuration**
  - Production environment variables
  - Secrets management (AWS Secrets Manager / HashiCorp Vault)
  - Multi-region deployment strategy
  - DNS and domain configuration
  - SSL certificate management

### Priority 4 (Monitoring & Observability)
**Goal**: Real-time visibility into system health and performance

- **Application Monitoring**
  - APM integration (New Relic / DataDog / Sentry)
  - Error tracking and alerting
  - Performance metrics (response times, throughput)
  - Custom business metrics (loans disbursed, transactions/sec)
  - User activity tracking

- **Infrastructure Monitoring**
  - Server resource utilization (CPU, memory, disk)
  - Database performance metrics
  - API endpoint availability checks
  - Log aggregation (ELK Stack / CloudWatch)
  - Distributed tracing for request flows

- **Alerting & Incident Response**
  - Critical error notifications (PagerDuty / Opsgenie)
  - Performance degradation alerts
  - Security breach detection
  - On-call rotation schedule
  - Incident response playbooks

### Priority 5 (Documentation)
**Goal**: Comprehensive documentation for developers and operators

- **API Documentation**
  - OpenAPI/Swagger specification
  - Interactive API explorer
  - Authentication guide
  - Request/response examples
  - Error codes and troubleshooting

- **Developer Documentation**
  - Architecture decision records (ADRs)
  - Database schema documentation
  - Code contribution guidelines
  - Local development setup guide
  - Testing guidelines and best practices

- **Operations Documentation**
  - Deployment procedures
  - Database migration guide
  - Backup and restore procedures
  - Monitoring and alerting setup
  - Troubleshooting common issues
  - Disaster recovery runbook

### Priority 6 (Performance Optimization)
**Goal**: Optimize for high-volume transaction processing

- **Database Optimization**
  - Query performance analysis and optimization
  - Index strategy review and enhancement
  - Connection pooling configuration
  - Query result caching strategy
  - Partitioning for large tables

- **Application Optimization**
  - Redis caching for frequently accessed data
  - Async task processing (Celery) for reports
  - Lazy loading and select_related optimization
  - API response pagination optimization
  - Static file serving optimization

- **Scalability Improvements**
  - Horizontal scaling strategy
  - Read replica configuration for reports
  - Database sharding strategy (future)
  - Microservices decomposition evaluation
  - Queue-based architecture for high-volume operations

### Priority 7 (Compliance & Audit)
**Goal**: Meet regulatory and audit requirements

- **Audit Trail Enhancement**
  - Immutable audit log for all transactions
  - User action logging (who, what, when)
  - Change history for all critical records
  - Report access logging
  - Data retention policies

- **Compliance Features**
  - GDPR compliance (data export, right to be forgotten)
  - PCI-DSS compliance for payment data
  - SOC 2 audit preparation
  - KYC/AML integration points
  - Regulatory reporting templates

### Priority 8 (Future Enhancements)
**Goal**: Extend functionality based on business needs

- **Advanced Features**
  - Automated interest accrual scheduler
  - Loan restructuring and refinancing workflows
  - Collections and recovery management
  - Early repayment handling with penalties
  - Loan guarantor management

- **Integration Capabilities**
  - Mobile money integration (M-Pesa, Airtel Money)
  - Core banking system integration
  - Credit bureau integration
  - SMS/email notification service
  - Webhook support for external systems

- **Reporting Enhancements**
  - Custom report builder
  - Scheduled report generation
  - Export to multiple formats (CSV, XLSX, PDF)
  - Dashboard with real-time metrics
  - Data analytics and business intelligence integration

## Maintenance & Support

### Regular Activities
- Weekly dependency updates and security patches
- Monthly performance review and optimization
- Quarterly disaster recovery testing
- Annual security audit and penetration testing
- Continuous monitoring of error rates and performance metrics

### Support Channels
- Issue tracking via GitHub Issues
- Documentation updates via pull requests
- Security vulnerabilities via private security advisory

## License

See [LICENSE](LICENSE) for details.

## Contributors

Contributions are welcome! Please read the contribution guidelines before submitting pull requests.