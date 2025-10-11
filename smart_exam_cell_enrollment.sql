-- MySQL dump 10.13  Distrib 8.0.42, for Win64 (x86_64)
--
-- Host: localhost    Database: smart_exam_cell
-- ------------------------------------------------------
-- Server version	8.0.42

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `enrollment`
--

DROP TABLE IF EXISTS `enrollment`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `enrollment` (
  `enrollment_id` int NOT NULL AUTO_INCREMENT,
  `student_id` varchar(20) DEFAULT NULL,
  `section_id` int DEFAULT NULL,
  `enroll_date` date DEFAULT NULL,
  `status` varchar(20) DEFAULT 'Enrolled',
  `grade_mode` varchar(20) DEFAULT 'Letter',
  PRIMARY KEY (`enrollment_id`),
  KEY `student_id` (`student_id`),
  KEY `section_id` (`section_id`),
  CONSTRAINT `enrollment_ibfk_1` FOREIGN KEY (`student_id`) REFERENCES `student` (`student_id`),
  CONSTRAINT `enrollment_ibfk_2` FOREIGN KEY (`section_id`) REFERENCES `section` (`section_id`)
) ENGINE=InnoDB AUTO_INCREMENT=36 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `enrollment`
--

LOCK TABLES `enrollment` WRITE;
/*!40000 ALTER TABLE `enrollment` DISABLE KEYS */;
INSERT INTO `enrollment` VALUES (1,'CS2023001',1,'2025-08-15','Enrolled','Letter'),(2,'CS2023002',1,'2025-08-15','Enrolled','Letter'),(3,'CS2023003',1,'2025-08-15','Enrolled','Letter'),(4,'CS2023004',1,'2025-08-15','Enrolled','Letter'),(5,'CS2023005',1,'2025-08-15','Enrolled','Letter'),(6,'CS2023006',1,'2025-08-15','Enrolled','Letter'),(7,'CS2023007',1,'2025-08-15','Enrolled','Letter'),(8,'CS2023008',1,'2025-08-15','Enrolled','Letter'),(9,'CS2023009',1,'2025-08-15','Enrolled','Letter'),(10,'CS2023010',1,'2025-08-15','Enrolled','Letter'),(11,'CS2023011',1,'2025-08-15','Enrolled','Letter'),(12,'CS2023012',1,'2025-08-15','Enrolled','Letter'),(13,'CS2023013',1,'2025-08-15','Enrolled','Letter'),(14,'CS2023014',1,'2025-08-15','Enrolled','Letter'),(15,'CS2023015',1,'2025-08-15','Enrolled','Letter'),(16,'CS2023016',1,'2025-08-15','Enrolled','Letter'),(17,'CS2023017',1,'2025-08-15','Enrolled','Letter'),(18,'CS2023018',1,'2025-08-15','Enrolled','Letter'),(19,'CS2023019',1,'2025-08-15','Enrolled','Letter'),(20,'CS2023020',1,'2025-08-15','Enrolled','Letter'),(21,'IT2023001',2,'2025-08-15','Enrolled','Letter'),(22,'IT2023002',2,'2025-08-15','Enrolled','Letter'),(23,'IT2023003',2,'2025-08-15','Enrolled','Letter'),(24,'IT2023004',2,'2025-08-15','Enrolled','Letter'),(25,'IT2023005',2,'2025-08-15','Enrolled','Letter'),(26,'IT2023006',2,'2025-08-15','Enrolled','Letter'),(27,'IT2023007',2,'2025-08-15','Enrolled','Letter'),(28,'IT2023008',2,'2025-08-15','Enrolled','Letter'),(29,'IT2023009',2,'2025-08-15','Enrolled','Letter'),(30,'IT2023010',2,'2025-08-15','Enrolled','Letter'),(31,'IT2023011',2,'2025-08-15','Enrolled','Letter'),(32,'IT2023012',2,'2025-08-15','Enrolled','Letter'),(33,'IT2023013',2,'2025-08-15','Enrolled','Letter'),(34,'IT2023014',2,'2025-08-15','Enrolled','Letter'),(35,'IT2023015',2,'2025-08-15','Enrolled','Letter');
/*!40000 ALTER TABLE `enrollment` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-09-28 21:26:02
