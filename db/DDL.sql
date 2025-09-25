-- =================================================================================================
-- FULL DDL SCRIPT (FINAL VERSION - ENGLISH STANDARD)
-- Includes Tables, Stored Procedures with all bug fixes, and the scheduled Event.
-- =================================================================================================

-- ----------------------------
-- Script Initial Settings
-- ----------------------------
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;
SET time_zone = '-03:00'; -- IMPORTANT: Sets the timezone for the Event Scheduler

-- ----------------------------
-- Database Structure
-- ----------------------------
DROP DATABASE IF EXISTS `bills_db`;
CREATE DATABASE `bills_db` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `bills_db`;

-- ----------------------------
-- Table: users
-- ----------------------------
DROP TABLE IF EXISTS `users`;
CREATE TABLE `users`  (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `email` varchar(255) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `cumulative_budget` tinyint(1) NULL DEFAULT 0,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `email_UNIQUE`(`email`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- ----------------------------
-- Table: categories
-- ----------------------------
DROP TABLE IF EXISTS `categories`;
CREATE TABLE `categories`  (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `name` varchar(100) NOT NULL,
  `budget_amount` decimal(10, 2) NULL DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `user_category_name_UNIQUE`(`user_id`, `name`) USING BTREE,
  CONSTRAINT `fk_categories_users` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE NO ACTION
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- ----------------------------
-- Table: bills
-- ----------------------------
DROP TABLE IF EXISTS `bills`;
CREATE TABLE `bills`  (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `category_id` int NOT NULL,
  `description` varchar(255) NOT NULL,
  `amount` decimal(10, 2) NOT NULL,
  `transaction_date` date NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  CONSTRAINT `fk_bills_categories_history` FOREIGN KEY (`category_id`) REFERENCES `categories` (`id`) ON DELETE RESTRICT ON UPDATE NO ACTION,
  CONSTRAINT `fk_bills_users_history` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE NO ACTION
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- ----------------------------
-- Table: monthly_budget_history
-- ----------------------------
DROP TABLE IF EXISTS `monthly_budget_history`;
CREATE TABLE `monthly_budget_history` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `category_id` INT NOT NULL,
  `period` DATE NOT NULL,
  `base_budget` DECIMAL(10, 2) NOT NULL,
  `monthly_spend` DECIMAL(10, 2) NOT NULL,
  `starting_balance` DECIMAL(10, 2) NOT NULL,
  `ending_balance` DECIMAL(10, 2) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE INDEX `category_period_UNIQUE` (`category_id`, `period`),
  CONSTRAINT `fk_history_categories` FOREIGN KEY (`category_id`) REFERENCES `categories` (`id`) ON DELETE CASCADE ON UPDATE NO ACTION
) ENGINE = InnoDB;


-- =================================================================================================
-- STORED PROCEDURES (FINAL CORRECTED VERSION)
-- =================================================================================================

-- ----------------------------
-- Procedure 1: Recalculates the full history for a single user.
-- ----------------------------
DROP PROCEDURE IF EXISTS `sp_recalculate_user_history`;
CREATE PROCEDURE `sp_recalculate_user_history`(IN p_user_id INT)
BEGIN
    DECLARE v_done INT DEFAULT FALSE;
    DECLARE v_category_id INT;
    DECLARE v_period DATE;
    DECLARE v_budget_amount DECIMAL(10, 2);
    DECLARE v_monthly_spend DECIMAL(10, 2);
    
    DECLARE v_current_category_id INT DEFAULT -1;
    DECLARE v_running_balance DECIMAL(10, 2) DEFAULT 0;

    DECLARE cur_expenses CURSOR FOR
        SELECT 
            c.id, 
            IFNULL(c.budget_amount, 0), -- Handles NULL budget_amount
            DATE_FORMAT(b.transaction_date, '%Y-%m-01'), 
            SUM(b.amount)
        FROM bills b
        JOIN categories c ON b.category_id = c.id
        WHERE b.user_id = p_user_id
        GROUP BY c.id, c.budget_amount, DATE_FORMAT(b.transaction_date, '%Y-%m-01')
        ORDER BY c.id ASC, DATE_FORMAT(b.transaction_date, '%Y-%m-01') ASC;

    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_done = TRUE;

    DELETE FROM monthly_budget_history WHERE category_id IN (SELECT id FROM categories WHERE user_id = p_user_id);

    OPEN cur_expenses;
    calculation_loop: LOOP
        FETCH cur_expenses INTO v_category_id, v_budget_amount, v_period, v_monthly_spend;
        IF v_done THEN
            LEAVE calculation_loop;
        END IF;

        IF v_category_id <> v_current_category_id THEN
            SET v_current_category_id = v_category_id;
            SET v_running_balance = 0;
        END IF;

        INSERT INTO monthly_budget_history (category_id, period, base_budget, monthly_spend, starting_balance, ending_balance)
        VALUES (
            v_category_id,
            v_period,
            v_budget_amount,
            v_monthly_spend,
            v_running_balance,
            (v_running_balance + v_budget_amount) - v_monthly_spend
        );
        
        SET v_running_balance = (v_running_balance + v_budget_amount) - v_monthly_spend;

    END LOOP;
    CLOSE cur_expenses;
END;

-- ----------------------------
-- Procedure 2: Optimized for the scheduled event (Monthly Closing).
-- ----------------------------
DROP PROCEDURE IF EXISTS `sp_execute_monthly_closing`;
CREATE PROCEDURE `sp_execute_monthly_closing`()
BEGIN
    DECLARE v_previous_month DATE;
    SET v_previous_month = DATE_FORMAT(CURDATE() - INTERVAL 1 MONTH, '%Y-%m-01');

    INSERT INTO monthly_budget_history (category_id, period, base_budget, monthly_spend, starting_balance, ending_balance)
    SELECT
        spendings.category_id,
        v_previous_month,
        spendings.budget_amount,
        spendings.total_spend,
        IFNULL(previous_history.ending_balance, 0) AS starting_balance,
        (IFNULL(previous_history.ending_balance, 0) + spendings.budget_amount) - spendings.total_spend AS ending_balance
    FROM
        (SELECT
            c.id AS category_id,
            IFNULL(c.budget_amount, 0) as budget_amount, -- Handles NULL budget_amount
            SUM(b.amount) AS total_spend
        FROM bills b
        JOIN categories c ON b.category_id = c.id
        JOIN users u ON c.user_id = u.id
        WHERE u.cumulative_budget = 1
          AND b.transaction_date >= v_previous_month
          AND b.transaction_date < (v_previous_month + INTERVAL 1 MONTH)
        GROUP BY c.id, c.budget_amount
        ) AS spendings
    LEFT JOIN
        monthly_budget_history previous_history ON spendings.category_id = previous_history.category_id
                                                  AND previous_history.period = (v_previous_month - INTERVAL 1 MONTH);
END;


-- =================================================================================================
-- EVENT SCHEDULER
-- =================================================================================================
DROP EVENT IF EXISTS `evt_monthly_budget_closing`;
CREATE EVENT `evt_monthly_budget_closing`
ON SCHEDULE
    EVERY 1 MONTH
    STARTS TIMESTAMP(DATE_FORMAT(NOW() + INTERVAL 1 MONTH, '%Y-%m-01'), '03:00:00') -- Runs on the 1st of each month at 3:00 AM.
DO
BEGIN
    CALL sp_execute_monthly_closing();
END;

-- ----------------------------
-- Script Finalization
-- ----------------------------
SET FOREIGN_KEY_CHECKS = 1;