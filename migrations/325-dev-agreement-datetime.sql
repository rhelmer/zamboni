ALTER TABLE `users` CHANGE COLUMN
    `read_dev_agreement` `read_dev_agreement` DATETIME;
UPDATE `users` SET `read_dev_agreement` = NULL
    WHERE `read_dev_agreement` = '0000-00-00 00:00:00';
