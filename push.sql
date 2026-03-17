-- ================================
-- Insert Courses
-- ================================

INSERT INTO "Course" ("CourseName", "Type")
VALUES 
('Supervised Learning', 'ML'),
('Unsupervised Learning', 'ML'),
('Pre-requisite course', 'Foundation');

-- ================================
-- Insert Modules
-- ================================

-- Supervised Learning Modules
INSERT INTO "Module" ("CourseId", "ModuleName")
SELECT c."CourseId", m.module_name
FROM "Course" c
JOIN (
    VALUES 
    ('linear regression'),
    ('logistic regression'),
    ('KNN'),
    ('Decision Tree'),
    ('SVM'),
    ('naive bayes'),
    ('Ensemble Learning'),
    ('Random forest')
) AS m(module_name)
ON c."CourseName" = 'Supervised Learning';

-- Unsupervised Learning Modules
INSERT INTO "Module" ("CourseId", "ModuleName")
SELECT c."CourseId", m.module_name
FROM "Course" c
JOIN (
    VALUES 
    ('K-means clustering'),
    ('DBSCAN'),
    ('Hierarchical Clustering'),
    ('PCA')
) AS m(module_name)
ON c."CourseName" = 'Unsupervised Learning';

-- Pre-requisite Course Modules
INSERT INTO "Module" ("CourseId", "ModuleName")
SELECT c."CourseId", m.module_name
FROM "Course" c
JOIN (
    VALUES 
    ('Basics'),
    ('Data'),
    ('Math'),
    ('ML-workflow')
) AS m(module_name)
ON c."CourseName" = 'Pre-requisite course';