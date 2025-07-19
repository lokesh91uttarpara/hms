-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Generation Time: Jul 19, 2025 at 01:35 PM
-- Server version: 10.4.28-MariaDB
-- PHP Version: 8.0.28

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `hotel_db`
--

-- --------------------------------------------------------

--
-- Table structure for table `md_room`
--

CREATE TABLE `md_room` (
  `id` int(11) NOT NULL,
  `room_no` varchar(20) NOT NULL,
  `room_size` enum('SB','DB','DT') NOT NULL,
  `room_type` enum('AC','NAC','DL') NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `created_by` varchar(100) DEFAULT NULL,
  `created_ip` varchar(45) DEFAULT NULL,
  `modified_date` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `modified_by` varchar(100) DEFAULT NULL,
  `modified_ip` varchar(45) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `md_room`
--

INSERT INTO `md_room` (`id`, `room_no`, `room_size`, `room_type`, `created_at`, `created_by`, `created_ip`, `modified_date`, `modified_by`, `modified_ip`) VALUES
(1, '1010', 'SB', 'NAC', '2025-07-19 11:02:59', NULL, NULL, '2025-07-19 11:29:13', NULL, NULL),
(9, '100', 'SB', 'AC', '2025-07-19 11:33:23', NULL, NULL, '2025-07-19 11:33:23', NULL, NULL);

-- --------------------------------------------------------

--
-- Table structure for table `md_user`
--

CREATE TABLE `md_user` (
  `id` int(10) NOT NULL,
  `user_id` varchar(200) NOT NULL,
  `pass` varchar(200) NOT NULL,
  `user_type` enum('A','M','U') NOT NULL,
  `user_status` enum('A','I') NOT NULL DEFAULT 'A'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `md_user`
--

INSERT INTO `md_user` (`id`, `user_id`, `pass`, `user_type`, `user_status`) VALUES
(1, 'abc@gmail.com', '$2b$12$yQSFV42LKzkbLiN38HfSvOs9b4Mjtq/NjNPWlhVqJ5tlJYqLisfzG', 'A', 'A');

--
-- Indexes for dumped tables
--

--
-- Indexes for table `md_room`
--
ALTER TABLE `md_room`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `room_no` (`room_no`),
  ADD KEY `idx_room_no` (`room_no`),
  ADD KEY `idx_room_size` (`room_size`),
  ADD KEY `idx_room_type` (`room_type`),
  ADD KEY `idx_created_at` (`created_at`);

--
-- Indexes for table `md_user`
--
ALTER TABLE `md_user`
  ADD PRIMARY KEY (`id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `md_room`
--
ALTER TABLE `md_room`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=10;

--
-- AUTO_INCREMENT for table `md_user`
--
ALTER TABLE `md_user`
  MODIFY `id` int(10) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
