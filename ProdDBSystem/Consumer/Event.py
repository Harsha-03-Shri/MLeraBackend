"""Event handler functions for processing SQS-triggered database operations.

Each function corresponds to an event type dispatched by the Lambda consumer
and performs the appropriate database read or write operation.
"""

import json
import logging
from Resorces import Database
import datetime

logging.basicConfig(level=logging.INFO)

db = Database()


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

        cursor.execute('INSERT INTO "UserCourse" ("UserId", "CourseId") VALUES (%s, %s)', (userId, courseId[0]))
        conn.commit()
        cursor.close()
        logging.info("Inserted course purchase for user: %s, course: %s", userId, courseName)

    except Exception as e:
        logging.error(f"Error while processing course purchase: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            db.releaseDBconnection(conn)


def courseProgress(data):
    """Calculate and return a user's progress for a given course.

    Args:
        data: Dict containing userId and courseName.

    Returns:
        A dict with totalModules, inProgress, and completed counts,
        or None if required data is missing or not found.
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

        cursor.execute('SELECT COUNT(*) FROM "Module" WHERE "CourseId" = %s', (courseId[0],))
        totalModules = cursor.fetchone()[0]

        cursor.execute('SELECT "Completed" FROM "UserModuleProgress" WHERE "UserId" = %s', (userId,))
        progress = cursor.fetchall()
        cursor.close()

        inprogress = 0
        completed = 0
        for row in progress:
            if not row[0]:
                inprogress += 1
            else:
                completed += 1

        logging.info("Fetched course progress for user: %s, course: %s", userId, courseName)
        return {
            "totalModules": totalModules,
            "inProgress": inprogress,
            "completed": completed
        }

    except Exception as e:
        logging.error(f"Error while processing course progress: {e}")
    finally:
        if conn:
            db.releaseDBconnection(conn)


def resumeModule(data):
    """Fetch the last visited page for a user's module.

    Args:
        data: Dict containing userId and moduleName.

    Returns:
        A dict with userId, moduleName, and LastPage,
        or None if required data is missing or not found.
    """
    conn = None
    try:
        userId = data.get("userId")
        moduleName = data.get("moduleName")

        if not all([userId, moduleName]):
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

        cursor.execute('SELECT "Page" FROM "UserModuleProgress" WHERE "UserId" = %s AND "ModuleId" = %s', (userId, moduleId[0]))
        progress = cursor.fetchone()
        logging.info(f"{progress[0] if progress else None}")
        cursor.close()

        return {
            "userId": userId,
            "moduleName": moduleName,
            "LastPage": progress[0] if progress else None
        }

    except Exception as e:
        logging.error(f"Error while processing resume module: {e}")
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
        Page = data.get("LastPage")

        if not all([userId, moduleName, Page]):
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
            'INSERT INTO "UserModuleProgress" ("UserId", "ModuleId", "Page", "Completed") VALUES (%s, %s, %s, %s) ON CONFLICT ("UserId", "ModuleId") DO UPDATE SET "Page" = %s',
            (userId, moduleId[0], Page, False, Page)
        )
        conn.commit()
        cursor.close()
        logging.info("Updated module progress for user: %s, module: %s, page: %s", userId, moduleName, Page)

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
