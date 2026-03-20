CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE "User" (
    "UserId" UUID PRIMARY KEY,
    "Name" TEXT,
    "Profession" TEXT,
    "Phone" TEXT,
    "Email" TEXT UNIQUE,
    "CreatedOn" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE "Auth" (
    "Email" TEXT PRIMARY KEY,
    "PasswordHash" TEXT NOT NULL,
    "UserId" UUID,
    FOREIGN KEY ("UserId") REFERENCES "User"("UserId") ON DELETE CASCADE
);

CREATE TABLE "Course" (
    "CourseId" UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    "Type" TEXT,
    "CourseName" TEXT UNIQUE
);

CREATE TABLE "Module" (
    "ModuleId" UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    "CourseId" UUID,
    "ModuleName" TEXT,
    FOREIGN KEY ("CourseId") REFERENCES "Course"("CourseId") ON DELETE CASCADE
);

CREATE TABLE "UserCourse" (
    "UserId" UUID,
    "CourseId" UUID,
    PRIMARY KEY ("UserId","CourseId"),
    FOREIGN KEY ("UserId") REFERENCES "User"("UserId") ON DELETE CASCADE,
    FOREIGN KEY ("CourseId") REFERENCES "Course"("CourseId") ON DELETE CASCADE
);

CREATE TABLE "UserModuleProgress" (
    "UserId" UUID,
    "ModuleId" UUID,
    "Page" TEXT,
    "Completed" BOOLEAN DEFAULT FALSE,
    "CompletedOn" TIMESTAMP,
    PRIMARY KEY ("UserId","ModuleId"),
    FOREIGN KEY ("UserId") REFERENCES "User"("UserId") ON DELETE CASCADE,
    FOREIGN KEY ("ModuleId") REFERENCES "Module"("ModuleId") ON DELETE CASCADE
);

CREATE TABLE "Quiz" (
    "QuizId" UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    "UserId" UUID,
    "ModuleId" UUID,
    "Percent" INTEGER,
    "Pass" BOOLEAN,
    "AttemptedOn" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY ("UserId") REFERENCES "User"("UserId") ON DELETE CASCADE,
    FOREIGN KEY ("ModuleId") REFERENCES "Module"("ModuleId") ON DELETE CASCADE
);

CREATE TABLE "PracticeQuiz" (
    "UserId" UUID,
    "ModuleId" UUID,
    "HighestScore" INTEGER,
    "LowestScore" INTEGER,
    "Attempts" INTEGER DEFAULT 0,
    PRIMARY KEY ("UserId","ModuleId"),
    FOREIGN KEY ("UserId") REFERENCES "User"("UserId") ON DELETE CASCADE,
    FOREIGN KEY ("ModuleId") REFERENCES "Module"("ModuleId") ON DELETE CASCADE
);