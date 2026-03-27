# MLera Backend API Documentation

## Base URL
```
Production: http://mleraalb-1595386243.ap-south-1.elb.amazonaws.com
Local: http://localhost
```

---

## Table of Contents
1. [Authentication](#authentication)
2. [User Management](#user-management)
3. [Course Management](#course-management)
4. [Module Management](#module-management)
5. [Practice Quiz](#practice-quiz)
6. [Notifications](#notifications)
7. [Health Checks](#health-checks)

---

## Authentication

All protected endpoints require a JWT token in the Authorization header:

```
Authorization: Bearer <your_jwt_token>
```

### How to Get Token
1. Register a user via `/user/register`
2. Login via `/user/login` to receive JWT token
3. Use token in subsequent requests

---

## User Management

### 1. Register User

**Endpoint:** `POST /user/register`

**Description:** Creates a new user account with hashed password, sets up notification preferences, and sends welcome email.

**Authentication:** None (Public)

**Request Body:**
```json
{
  "Name": "John Doe",
  "Phone": "9876543210",
  "Email": "john.doe@example.com",
  "Profession": "Software Engineer",
  "Password": "securePassword123"
}
```

**Validation Rules:**
- `Name`: 3-25 characters
- `Phone`: Minimum 10 characters
- `Email`: Valid email format
- `Profession`: Minimum 3 characters
- `Password`: Minimum 6 characters

**Response:** `200 OK`
```json
{
  "message": "User registered successfully"
}
```

**What Happens:**
1. Generates unique UUID for user
2. Hashes password with bcrypt
3. Stores user in PostgreSQL `User` and `Auth` tables
4. Creates user profile in DynamoDB (Notification service)
5. Sends registration confirmation email via SNS → SQS → Lambda

**Error Responses:**
- `500`: Database error or email already exists

---

### 2. Login User

**Endpoint:** `POST /user/login`

**Description:** Authenticates user credentials and returns JWT token valid for 1 hour.

**Authentication:** None (Public)

**Request Body:**
```json
{
  "Email": "john.doe@example.com",
  "Password": "securePassword123"
}
```

**Response:** `200 OK`
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**What Happens:**
1. Queries `Auth` table for email
2. Verifies password hash using bcrypt
3. Generates JWT token with userId and 1-hour expiration
4. Returns token for subsequent authenticated requests

**Error Responses:**
- `401`: Invalid email or password
- `500`: Internal server error

---

### 3. Get User Profile

**Endpoint:** `GET /user/profile`

**Description:** Retrieves authenticated user's profile information including enrolled courses.

**Authentication:** Required (JWT Bearer Token)

**Request Headers:**
```
Authorization: Bearer <jwt_token>
```

**Response:** `200 OK`
```json
{
  "Name": "John Doe",
  "Profession": "Software Engineer",
  "Phone": "9876543210",
  "Email": "john.doe@example.com"
}
```

**What Happens:**
1. Validates JWT token and extracts userId
2. Checks Redis cache for profile data
3. If cache miss, queries PostgreSQL `User` table
4. Caches result in Redis for faster subsequent requests
5. Returns user profile

**Error Responses:**
- `401`: Invalid or expired token
- `404`: User not found
- `500`: Internal server error

---

### 4. Delete User Account

**Endpoint:** `POST /user/delete`

**Description:** Permanently deletes authenticated user's account and all associated data, then sends a confirmation email.

**Authentication:** Required (JWT Bearer Token)

**Request Headers:**
```
Authorization: Bearer <jwt_token>
```

**Response:** `200 OK`
```json
{
  "message": "Account deleted successfully"
}
```

**What Happens:**
1. Validates JWT token and extracts userId
2. Sends delete event to DB API
3. DB API sends event to SQS queue and clears Redis cache
4. Lambda consumer processes event:
   - Deletes user from `User` table
   - CASCADE automatically deletes from:
     - `Auth` (login credentials)
     - `UserCourse` (course enrollments)
     - `UserModuleProgress` (module progress)
     - `Quiz` (quiz attempts)
     - `PracticeQuiz` (practice quiz statistics)
5. Sends notification request to Notification API
6. Notification API:
   - Retrieves user data from DynamoDB
   - Fetches "AccountDeletion" email template
   - Formats confirmation message
   - Publishes to SNS → SQS → Lambda sends email

**Error Responses:**
- `401`: Invalid or expired token
- `500`: Internal server error

**Note:** This action is irreversible. All user data will be permanently deleted.

---

## Course Management

### 5. Purchase Course

**Endpoint:** `POST /course/purchase`

**Description:** Enrolls authenticated user in a course, granting access to all modules, and sends a course purchase notification email.

**Authentication:** Required (JWT Bearer Token)

**Request Headers:**
```
Authorization: Bearer <jwt_token>
```

**Request Body:**
```json
{
  "courseName": "Python Fundamentals"
}
```

**Response:** `200 OK`
```json
{
  "message": "Course 'Python Fundamentals' purchased successfully by user 123e4567-e89b-12d3-a456-426614174000"
}
```

**What Happens:**
1. Validates JWT token and extracts userId
2. Sends purchase event to DB API
3. DB API processes event:
   - Looks up courseId from `Course` table
   - Inserts record into `UserCourse` table
4. Sends notification request to Notification API with CourseName
5. Notification API sends "CoursePurchase" email to user
6. Caches purchase in Redis

**Error Responses:**
- `401`: Invalid or expired token
- `404`: Course not found
- `500`: Internal server error

---

### 6. Get Course Progress

**Endpoint:** `GET /course/progress?courseName=<course_name>`

**Description:** Fetches course progress statistics showing completed, in-progress, and pending modules.

**Authentication:** Required (JWT Bearer Token)

**Request Headers:**
```
Authorization: Bearer <jwt_token>
```

**Query Parameters:**
- `courseName` (required): Name of the course

**Example:**
```
GET /course/progress?courseName=Python%20Fundamentals
```

**Response:** `200 OK`
```json
{
  "totalModules": 10,
  "inProgress": 3,
  "completed": 5
}
```

**What Happens:**
1. Validates JWT token and extracts userId
2. Checks Redis cache for progress data
3. If cache miss, sends request to DB API
4. DB API queries:
   - Total modules in course from `Module` table
   - User's progress from `UserModuleProgress` table
5. Calculates completed vs in-progress modules
6. Caches result in Redis

**Error Responses:**
- `401`: Invalid or expired token
- `404`: Course not found
- `500`: Internal server error

---

## Module Management

### 7. Update Module Progress

**Endpoint:** `POST /module/update`

**Description:** Records the current page/section user is studying to enable resume functionality.

**Authentication:** Required (JWT Bearer Token)

**Request Headers:**
```
Authorization: Bearer <jwt_token>
```

**Request Body:**
```json
{
  "ModuleName": "Introduction to Python",
  "PageName": "Variables and Data Types"
}
```

**Response:** `200 OK`
```json
{
  "message": "Progress for module 'Introduction to Python' updated successfully for user 123e4567-e89b-12d3-a456-426614174000"
}
```

**What Happens:**
1. Validates JWT token and extracts userId
2. Sends update event to SQS queue
3. Lambda consumer processes event:
   - Looks up moduleId from `Module` table
   - Upserts record in `UserModuleProgress` table with page number
   - Sets `Completed` = false
4. Invalidates Redis cache for resume data

**Error Responses:**
- `401`: Invalid or expired token
- `404`: Module not found
- `500`: Internal server error

---

### 8. Complete Module

**Endpoint:** `POST /module/complete`

**Description:** Marks module as completed with quiz score and triggers completion notification email.

**Authentication:** Required (JWT Bearer Token)

**Request Headers:**
```
Authorization: Bearer <jwt_token>
```

**Request Body:**
```json
{
  "ModuleName": "Introduction to Python",
  "QuizPercentage": 85.5
}
```

**Validation Rules:**
- `QuizPercentage`: 0-100, required
- `ModuleName`: Required

**Response:** `200 OK`
```json
{
  "message": "Module 'Introduction to Python' completed successfully for user 123e4567-e89b-12d3-a456-426614174000"
}
```

**What Happens:**
1. Validates JWT token and extracts userId
2. Sends completion event to DB API
3. DB API processes event:
   - Looks up moduleId from `Module` table
   - Updates `UserModuleProgress`: `Completed` = true, `CompletedOn` = timestamp
   - Inserts quiz record into `Quiz` table with score
4. Sends notification request to Notification API with ModuleName and QuizPercentage
5. Notification API:
   - Retrieves user data from DynamoDB
   - Fetches "ModuleCompletion" email template
   - Formats message with user name, module name, and quiz score
   - Publishes to SNS → SQS → Lambda sends email

**Error Responses:**
- `401`: Invalid or expired token
- `404`: Module not found
- `500`: Internal server error

---

### 9. Resume Module

**Endpoint:** `GET /module/resume?moduleName=<module_name>`

**Description:** Retrieves the last page user accessed in a module to continue from where they left off.

**Authentication:** Required (JWT Bearer Token)

**Request Headers:**
```
Authorization: Bearer <jwt_token>
```

**Query Parameters:**
- `moduleName` (required): Name of the module

**Example:**
```
GET /module/resume?moduleName=Introduction%20to%20Python
```

**Response:** `200 OK`
```json
{
  "lastPage": "Variables and Data Types"
}
```

**What Happens:**
1. Validates JWT token and extracts userId
2. Checks Redis cache for resume data
3. If cache miss, sends request to DB API
4. DB API queries `UserModuleProgress` table for last saved page
5. Caches result in Redis

**Error Responses:**
- `401`: Invalid or expired token
- `404`: Module not found or no progress saved
- `500`: Internal server error

---

## Practice Quiz

### 10. Submit Practice Quiz

**Endpoint:** `POST /practicequiz/submit`

**Description:** Submits practice quiz score and updates user's quiz statistics (highest, lowest, attempts).

**Authentication:** Required (JWT Bearer Token)

**Request Headers:**
```
Authorization: Bearer <jwt_token>
```

**Request Body:**
```json
{
  "moduleName": "Introduction to Python",
  "score": 85
}
```

**Response:** `200 OK`
```json
{
  "message": "Quiz submitted successfully"
}
```

**What Happens:**
1. Validates JWT token and extracts userId
2. Sends submission event to SQS queue
3. Lambda consumer processes event:
   - Looks up moduleId from `Module` table
   - Upserts record in `PracticeQuiz` table:
     - Updates `HighestScore` if current score is higher
     - Updates `LowestScore` if current score is lower
     - Increments `Attempts` counter
4. Updates Redis cache with new statistics

**Error Responses:**
- `401`: Invalid or expired token
- `404`: Module not found
- `500`: Internal server error

---

### 11. Get Practice Quiz Report

**Endpoint:** `GET /practicequiz/report?moduleName=<module_name>`

**Description:** Retrieves comprehensive quiz performance statistics for a specific module.

**Authentication:** Required (JWT Bearer Token)

**Request Headers:**
```
Authorization: Bearer <jwt_token>
```

**Query Parameters:**
- `moduleName` (required): Name of the module

**Example:**
```
GET /practicequiz/report?moduleName=Introduction%20to%20Python
```

**Response:** `200 OK`
```json
{
  "HighestScore": 95,
  "LowestScore": 65,
  "Attempts": 5
}
```

**What Happens:**
1. Validates JWT token and extracts userId
2. Checks Redis cache for report data
3. If cache miss, queries DB API
4. DB API queries `PracticeQuiz` table for user's statistics
5. Caches result in Redis

**Error Responses:**
- `401`: Invalid or expired token
- `404`: Module not found or no quiz attempts
- `500`: Internal server error

---

## Notifications

### 12. Create User in Notification System

**Endpoint:** `POST /api/v1/user/create`

**Description:** Creates user profile in DynamoDB for notification preferences (called internally by Main API during registration).

**Authentication:** None (Internal API)

**Request Body:**
```json
{
  "userId": "123e4567-e89b-12d3-a456-426614174000",
  "name": "John Doe",
  "email": "john.doe@example.com"
}
```

**Response:** `200 OK`
```json
{
  "user_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

**What Happens:**
1. Stores user data in DynamoDB `Users` table
2. Sets default notification channel to "email"
3. Prepares user for receiving notifications

**Error Responses:**
- `500`: DynamoDB write error

---

### 13. Send Notification

**Endpoint:** `POST /notify/`

**Description:** Sends event-based notification to user (registration, module completion, etc.).

**Authentication:** None (Internal API)

**Request Body:**

**For Registration:**
```json
{
  "userId": "123e4567-e89b-12d3-a456-426614174000",
  "TemplateType": "Registration"
}
```

**For Module Completion:**
```json
{
  "userId": "123e4567-e89b-12d3-a456-426614174000",
  "TemplateType": "ModuleCompletion",
  "ModuleName": "Introduction to Python",
  "QuizPercentage": 85
}
```

**For Course Purchase:**
```json
{
  "userId": "123e4567-e89b-12d3-a456-426614174000",
  "TemplateType": "CoursePurchase",
  "CourseName": "Python Fundamentals"
}
```

**For Account Deletion:**
```json
{
  "userId": "123e4567-e89b-12d3-a456-426614174000",
  "TemplateType": "AccountDeletion"
}
```

**Response:** `200 OK`
```json
{
  "message": "Notification sent successfully"
}
```

**What Happens:**
1. Retrieves user data from DynamoDB `Users` table
2. Validates required fields based on TemplateType:
   - ModuleCompletion: Requires `ModuleName` and `QuizPercentage`
   - CoursePurchase: Requires `CourseName`
   - AccountDeletion: No additional fields required
3. Fetches email template from DynamoDB `Templates` table
4. Formats message by replacing placeholders:
   - `{Name}` → User's name
   - `{ModuleName}` → Module name (for ModuleCompletion)
   - `{QuizPercentage}` → Quiz score (for ModuleCompletion)
   - `{CourseName}` → Course name (for CoursePurchase)
5. Publishes message to SNS topic with channel filter
6. SNS routes to appropriate SQS queue (email, apn, fcm)
7. Lambda consumer processes queue:
   - Email Lambda sends via Gmail SMTP
   - Other channels handled by respective consumers

**Error Responses:**
- `400`: Missing required fields (e.g., QuizPercentage and ModuleName for ModuleCompletion, CourseName for CoursePurchase)
- `404`: User or template not found
- `500`: SNS publish error or message formatting failure

---

## Health Checks

### 14. Nginx Health Check

**Endpoint:** `GET /health`

**Description:** Checks if Nginx reverse proxy is running.

**Authentication:** None (Public)

**Response:** `200 OK`
```json
{
  "status": "healthy"
}
```

---

### 15. Main API Health Check

**Endpoint:** `GET /health` (on Main API container)

**Description:** Checks if Main API service is running.

**Authentication:** None (Public)

**Response:** `200 OK`
```json
{
  "status": "healthy"
}
```

---

### 16. DB API Health Check

**Endpoint:** `GET /health` (on DB API container)

**Description:** Checks if DB API service is running.

**Authentication:** None (Public)

**Response:** `200 OK`
```json
{
  "status": "healthy"
}
```

---

### 17. Notification API Health Check

**Endpoint:** `GET /health` (on Notification API container)

**Description:** Checks if Notification API service is running.

**Authentication:** None (Public)

**Response:** `200 OK`
```json
{
  "status": "healthy"
}
```

---

## Error Response Format

All endpoints return errors in this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

**Common HTTP Status Codes:**
- `200`: Success
- `400`: Bad request (validation error)
- `401`: Unauthorized (invalid/expired token)
- `404`: Resource not found
- `500`: Internal server error

---

## Data Flow Architecture

### User Registration Flow
```
Client → Main API → DB API → PostgreSQL
                  ↓
            Notification API → DynamoDB
                  ↓
                 SNS → SQS → Lambda → Gmail SMTP
```

### Course Purchase Flow
```
Client → Main API → DB API → SQS Queue
                              ↓
                         Lambda Consumer → PostgreSQL
                              ↓
                         Redis Cache
```

### Module Completion Flow
```
Client → Main API → DB API → PostgreSQL
                  ↓
            Notification API (ModuleName, QuizPercentage)
                  ↓
            DynamoDB (User + Template)
                  ↓
                 SNS → SQS → Lambda → Email
```

### Course Purchase Flow
```
Client → Main API → DB API → PostgreSQL
                  ↓
            Notification API (CourseName)
                  ↓
            DynamoDB (User + Template)
                  ↓
                 SNS → SQS → Lambda → Email
```

### Account Deletion Flow
```
Client → Main API → DB API → SQS Queue
                              ↓
                         Lambda Consumer → PostgreSQL (CASCADE DELETE)
                              ↓
                         Clears Redis Cache
                              ↓
                    Notification API (AccountDeletion)
                              ↓
                    DynamoDB (User + Template)
                              ↓
                         SNS → SQS → Lambda → Email
```

---

## Database Schema

### PostgreSQL Tables

**User**
- UserId (UUID, PK)
- Name (TEXT)
- Profession (TEXT)
- Phone (TEXT)
- Email (TEXT, UNIQUE)
- CreatedOn (TIMESTAMP)

**Auth**
- Email (TEXT, PK)
- PasswordHash (TEXT)
- UserId (UUID, FK → User)

**Course**
- CourseId (UUID, PK)
- Type (TEXT)
- CourseName (TEXT, UNIQUE)

**Module**
- ModuleId (UUID, PK)
- CourseId (UUID, FK → Course)
- ModuleName (TEXT)

**UserCourse**
- UserId (UUID, PK, FK → User)
- CourseId (UUID, PK, FK → Course)

**UserModuleProgress**
- UserId (UUID, PK, FK → User)
- ModuleId (UUID, PK, FK → Module)
- Page (INTEGER)
- Completed (BOOLEAN)
- CompletedOn (TIMESTAMP)

**Quiz**
- QuizId (UUID, PK)
- UserId (UUID, FK → User)
- ModuleId (UUID, FK → Module)
- Percent (INTEGER)
- Pass (BOOLEAN)
- AttemptedOn (TIMESTAMP)

**PracticeQuiz**
- UserId (UUID, PK, FK → User)
- ModuleId (UUID, PK, FK → Module)
- HighestScore (INTEGER)
- LowestScore (INTEGER)
- Attempts (INTEGER)

### DynamoDB Tables

**Users**
- userId (String, PK)
- channel (String, SK)
- id (String) - email address
- Name (String)

**Templates**
- TemplateType (String, PK)
- Channel (String, SK)
- TemplateId (String)
- Subject (String)
- Body (String)
- Version (Number)
- CreatedAt (String)

---

## Rate Limiting & Performance

- **Connection Pooling**: 
  - PostgreSQL: 1-10 connections
  - Redis: 10 max connections
  
- **Caching Strategy**:
  - User profiles cached in Redis
  - Course progress cached in Redis
  - Module resume data cached in Redis
  - Quiz reports cached in Redis

- **Async Processing**:
  - Course purchases processed via SQS
  - Module updates processed via SQS
  - Notifications sent via SNS → SQS → Lambda

---

## Security Considerations

1. **Password Security**: Bcrypt hashing with salt
2. **JWT Tokens**: 1-hour expiration, HS256 algorithm
3. **CORS**: Configured for specific origins (update in production)
4. **Environment Variables**: Sensitive data stored in .env
5. **Database**: Connection pooling prevents exhaustion
6. **API Gateway**: Nginx reverse proxy for routing

---

## Testing Examples

### Using cURL

**Register User:**
```bash
curl -X POST http://mleraalb-1595386243.ap-south-1.elb.amazonaws.com/user/register \
  -H "Content-Type: application/json" \
  -d '{
    "Name": "John Doe",
    "Phone": "9876543210",
    "Email": "john.doe@example.com",
    "Profession": "Software Engineer",
    "Password": "securePassword123"
  }'
```

**Login:**
```bash
curl -X POST http://mleraalb-1595386243.ap-south-1.elb.amazonaws.com/user/login \
  -H "Content-Type: application/json" \
  -d '{
    "Email": "john.doe@example.com",
    "Password": "securePassword123"
  }'
```

**Get Profile (with token):**
```bash
curl -X GET http://mleraalb-1595386243.ap-south-1.elb.amazonaws.com/user/profile \
  -H "Authorization: Bearer <your_jwt_token>"
```

**Purchase Course:**
```bash
curl -X POST http://mleraalb-1595386243.ap-south-1.elb.amazonaws.com/course/purchase \
  -H "Authorization: Bearer <your_jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "courseName": "Python Fundamentals"
  }'
```

---

## Support & Troubleshooting

**Common Issues:**

1. **401 Unauthorized**: Token expired or invalid
   - Solution: Login again to get new token

2. **404 Not Found**: Resource doesn't exist
   - Solution: Verify course/module names are correct

3. **500 Internal Server Error**: Server-side issue
   - Solution: Check logs with `docker-compose logs -f`

4. **Connection Timeout**: Network/security group issue
   - Solution: Verify ALB security group allows port 80

**Logs:**
```bash
# View all logs
docker-compose logs -f

# View specific service
docker-compose logs -f main-api
docker-compose logs -f db-api
docker-compose logs -f notification-api
```

---

## Version History

- **v1.0.0** (2024): Initial release with core functionality
  - User management
  - Course enrollment
  - Module progress tracking
  - Practice quizzes
  - Email notifications

---

## Contact & Support

For issues or questions, check:
- GitHub Issues: [Repository URL]
- Documentation: This file
- Deployment Guide: DEPLOYMENT.md
