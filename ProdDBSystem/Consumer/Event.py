"""Event handler functions for processing SQS-triggered database operations.

Each function corresponds to an event type dispatched by the Lambda consumer
and performs the appropriate database read or write operation.
"""

import json
import logging
from Resorces import Database
import datetime

logging.basicConfig(level=logging.INFO, format="%(filename)s - %(levelname)s - %(message)s")

db = Database()

courseQuery = {
    "supervised learning": {
        "query": 'INSERT INTO "UserModuleProgress" ("UserId", "ModuleId", "CompletedPage", "Completed", "LastSeenPage") VALUES (%s, %s, %s, %s, %s) ON CONFLICT ("UserId", "ModuleId") DO UPDATE SET "LastSeenPage" = EXCLUDED."LastSeenPage"',
        "modules": ["linear regression", "logistic regression"]
    },
    "unsupervised learning": {
        "query": 'INSERT INTO "UserModuleProgress" ("UserId", "ModuleId", "CompletedPage", "Completed", "LastSeenPage") VALUES (%s, %s, %s, %s, %s) ON CONFLICT ("UserId", "ModuleId") DO UPDATE SET "LastSeenPage" = EXCLUDED."LastSeenPage"',
        "modules": ["k-means clustering"]
    },
    "pre-requisite course": {
        "query": 'INSERT INTO "UserModuleProgress" ("UserId", "ModuleId", "CompletedPage", "Completed", "LastSeenPage") VALUES (%s, %s, %s, %s, %s) ON CONFLICT ("UserId", "ModuleId") DO UPDATE SET "LastSeenPage" = EXCLUDED."LastSeenPage"',
        "modules": ["basics"]
    }
}

def submitPracticeQuiz(data):
    """Insert a practice quiz score into the database.

    Args:
        data: Dict containing userId, moduleName, and score.
    """
    conn = None
    try:
        userId = data.get("userId")
        moduleName = data.get("moduleName")
        score = data.get("score")

        if not all([userId, moduleName, score]):
            logging.warning("Missing required fields in data: %s", json.dumps(data))
            return

        conn = db.getDBconnection()
        cursor = conn.cursor()
        cursor.execute('SELECT "ModuleId" FROM "Module" WHERE "ModuleName" = %s', (moduleName,))
        moduleId = cursor.fetchone()
        if not moduleId:
            logging.warning("Module not found for name: %s", moduleName)
            cursor.close()
            return

        cursor.execute('INSERT INTO "PracticeQuiz" ("UserId", "ModuleId", "HighestScore", "LowestScore", "Attempts") VALUES (%s, %s, %s, %s, %s) ON CONFLICT ("UserId", "ModuleId") DO UPDATE SET "HighestScore" = GREATEST("PracticeQuiz"."HighestScore", %s), "LowestScore" = LEAST("PracticeQuiz"."LowestScore", %s), "Attempts" = "PracticeQuiz"."Attempts" + 1', (userId, moduleId[0], score, score, 1, score, score))
        conn.commit()
        cursor.close()
        logging.info("Inserted practice quiz for user: %s, module: %s, score: %d", userId, moduleName, score)

    except Exception as e:
        logging.error(f"Error while processing practice quiz submission: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            db.releaseDBconnection(conn)


def purchaseCourse(data):
    """Insert a course purchase record into the database.

    Args:
        data: Dict containing userId and courseName.
    """
    conn = None
    try:
        userId = data.get("userId")
        courseName = data.get("courseName")

        if not all([userId, courseName]):
            logging.warning("Missing required fields in data: %s", json.dumps(data))
            return

        conn = db.getDBconnection()
        cursor = conn.cursor()
        cursor.execute('SELECT "CourseId" FROM "Course" WHERE "CourseName" = %s', (courseName,))
        courseId = cursor.fetchone()
        if not courseId:
            logging.warning("Course not found for name: %s", courseName)
            cursor.close()
            return
        cursor.execute('INSERT INTO "UserCourse" ("UserId", "CourseId") VALUES (%s, %s) ON CONFLICT ("UserId", "CourseId") DO NOTHING', (userId, courseId[0]))
        conn.commit()

        moduleList = courseQuery.get(courseName, {}).get("modules", [])

        if not moduleList:
            logging.warning("No modules found for course: %s", courseName)
            cursor.close()
            return

        cursor.execute('SELECT "ModuleId" FROM "Module" WHERE "ModuleName" = ANY(%s)', (moduleList,))
        moduleIds = [row[0] for row in cursor.fetchall()]
        conn.commit()

        for moduleId in moduleIds:
            cursor.execute(courseQuery[courseName]["query"], (userId, moduleId, [], False, "Conversation"))
        conn.commit()
        cursor.close()
        logging.info("Inserted course purchase for user: %s, course: %s", userId, courseName)
        logging.info("Initialized module progress for user: %s, course: %s, modules: %s", userId, courseName, moduleList)

    except Exception as e:
        logging.error(f"Error while processing course purchase: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            db.releaseDBconnection(conn)



def updateModule(data):
    """Update the last visited page for a user's module progress.

    Args:
        data: Dict containing userId, moduleName, and LastPage.
    """
    conn = None
    try:
        userId = data.get("userId")
        moduleName = data.get("moduleName")
        CompletedPage = data.get("CompletedPage")
        LastseenPage = data.get("LastseenPage")

        if not all([userId, moduleName, CompletedPage,LastseenPage]):
            logging.warning("Missing required fields in data: %s", json.dumps(data))
            return

        conn = db.getDBconnection()
        cursor = conn.cursor()
        cursor.execute('SELECT "ModuleId" FROM "Module" WHERE "ModuleName" = %s', (moduleName,))
        moduleId = cursor.fetchone()
        if not moduleId:
            logging.warning("Module not found for name: %s", moduleName)
            cursor.close()
            return

        cursor.execute(
            'INSERT INTO "UserModuleProgress" ("UserId", "ModuleId", "CompletedPage", "Completed", "LastSeenPage") VALUES (%s, %s, %s::text[], %s, %s) ON CONFLICT ("UserId", "ModuleId") DO UPDATE SET "LastSeenPage" = EXCLUDED."LastSeenPage", "CompletedPage" = CASE WHEN %s = ANY("UserModuleProgress"."CompletedPage") THEN "UserModuleProgress"."CompletedPage" ELSE array_append("UserModuleProgress"."CompletedPage", %s) END',
            (userId, moduleId[0], [CompletedPage], False, LastseenPage, CompletedPage, CompletedPage)
        )
        conn.commit()
        cursor.close()
        logging.info("Updated module progress for user: %s, module: %s, page: %s", userId, moduleName, CompletedPage)
    except Exception as e:
        logging.error(f"Error while processing update module: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            db.releaseDBconnection(conn)


def completeModule(data):
    """Mark a module as completed for a user.

    Args:
        data: Dict containing userId, moduleName, and QuizPercentage.
    """
    conn = None
    try:
        userId = data.get("userId")
        moduleName = data.get("moduleName")
        QuizPercentage = data.get("QuizPercentage")

        if not all([userId, moduleName]) or QuizPercentage is None:
            logging.warning("Missing required fields in data: %s", json.dumps(data))
            return
        if QuizPercentage < 70:
            logging.warning("Quiz percentage below passing threshold for user: %s, module: %s, percentage: %d", userId, moduleName, QuizPercentage)
            return f"Quiz percentage below passing threshold: {QuizPercentage}%"
            
        conn = db.getDBconnection()
        cursor = conn.cursor()
        cursor.execute('SELECT "ModuleId" FROM "Module" WHERE "ModuleName" = %s', (moduleName,))
        moduleId = cursor.fetchone()
        if not moduleId:
            logging.warning("Module not found for name: %s", moduleName)
            cursor.close()
            return

        cursor.execute(
            'UPDATE "UserModuleProgress" SET "Completed" = %s, "CompletedOn" = %s WHERE "UserId" = %s AND "ModuleId" = %s',
            (True, datetime.datetime.now(), userId, moduleId[0])
        )
        cursor.execute('INSERT INTO "Quiz" ("UserId", "ModuleId", "Percent", "Pass") VALUES (%s, %s, %s, %s)', (userId, moduleId[0], QuizPercentage, QuizPercentage >= 70))

        conn.commit()
        cursor.close()
        logging.info("Completed module for user: %s, module: %s", userId, moduleName)

    except Exception as e:
        logging.error(f"Error while processing complete module: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            db.releaseDBconnection(conn)

def deleteAccount(data):
    """Delete a user account and all associated data.
    
    Due to ON DELETE CASCADE constraints, this will automatically delete:
    - Auth credentials
    - UserCourse enrollments
    - UserModuleProgress records
    - Quiz attempts
    - PracticeQuiz statistics

    Args:
        data: Dict containing userId.
    """
    conn = None
    try:
        userId = data.get("userId")
        
        if not userId:
            logging.warning("Missing userId in data: %s", json.dumps(data))
            return
        
        conn = db.getDBconnection()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM "User" WHERE "UserId" = %s', (userId,))
        
        if cursor.rowcount == 0:
            logging.warning("User not found for userId: %s", userId)
            cursor.close()
            return
        
        conn.commit()
        cursor.close()
        logging.info("Deleted account for user: %s (cascade deleted all related data)", userId)

    except Exception as e:
        logging.error(f"Error while deleting account: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            db.releaseDBconnection(conn)
