# Database Dump

## Table: `users`

| id | username | role | email | password_hash | is_active | created_at | department_id |
|---|---|---|---|---|---|---|---|
| 1 | admin | Admin | hemanthd571+admin@gmail.com | scrypt:32768:8:1$YlcRYfHQvlTkh4RP$ab4f884b72e79806aef48f7c690f22921d4a8a8a8d66fb345312ef5bc3b55bf0a41daa4ca39580fba8ae958a1cfa0edb8affa655b93d031d9bfa3dbe62559adf | 1 | 2026-07-27 14:15:45 | NULL |
| 2 | hemanth | Admin | hemanthd571+hemanth@gmail.com | scrypt:32768:8:1$VRaKqB8FLLHTMuPE$714b6665826979299847fa0ae934c5561b8d40ecb5022cd734360833de159b40ab3215e99e085a54e7e2173714790e20d255fc946efdabf742f90f09f22172bc | 1 | 2026-07-27 14:26:53 | NULL |
| 3 | sharath | Faculty | hemanthd571+sharath@gmail.com | scrypt:32768:8:1$avldse9xNn9cIWrg$d415871269294b1622ad6e1f0c52644963912547b16cee572a386448aee6ffbe0d739a5cae341d57c50122cf9d87c53a17c2b572955b118106240530b3be3720 | 1 | 2026-07-27 14:27:46 | NULL |
| 4 | student | Student/Organizer | hemanthd571+student@gmail.com | scrypt:32768:8:1$tsRgLQOgZh67FlDO$0a9706d00497d6bed206a190a32aba8e72ec8edaf997abfb37ebd467f06e7f01c9f8a1dea7541396b0eb360a4967b4b8068acdf867a63ecd0bea9da785e405ed | 1 | 2026-07-27 14:30:31 | 1 |
| 5 | faculty | Faculty | hemanthd571+faculty@gmail.com | scrypt:32768:8:1$wJ4Xy5A7dmFiXZHZ$73a32a7ee2396344e60210df99865f65db345389481a11c8150c5503a521de3b679c5530b650272e5ab4cda179dbe38a728042b2b57add5aed4dac8e14335685 | 1 | 2026-07-27 14:30:31 | 1 |
| 6 | hod | HOD | hemanthd571+hod@gmail.com | scrypt:32768:8:1$SGFFagyvk6Q8BmQl$6c21126be32ce8a299a21e6af565d8fe72e7a1af6b0369f55eb603c281e773f7154c218db48b1c194dd48ebec4679c09d997d0a01a6e8c37cf705809278a62bc | 1 | 2026-07-27 14:30:31 | 1 |
| 7 | director | Director | hemanthd571+director@gmail.com | scrypt:32768:8:1$jFVTX28Rc7RV8NYe$11054e499c3b64be070e6d89e3baaa6c7a2357241e872bd2547df5608da140d1dd3fcfdd27ac6381e7e881de2d3a0fed5e06a748481056595ce731e9ebfce39d | 1 | 2026-07-27 14:30:31 | 1 |
| 8 | provc | Pro VC | hemanthd571+provc@gmail.com | scrypt:32768:8:1$A4lfQuNEtcdplb9J$62c0452e841b06ab94d02c52cfda392298cb0a04d78a752d53625c6ff38a4fc375e8be7c35045ca320894820b6ea83b859a9caff62e9fe3b8d48573d086c7bfb | 1 | 2026-07-27 14:30:31 | 1 |
| 9 | vc | VC | hemanthd571+vc@gmail.com | scrypt:32768:8:1$FiXiSzrbkWtzxLt7$c1d659bcc2dd234648d6a7cde9ac61f171c5be00ad6b1d260d2ab1db39d2d66a19b255e315b969ade3d3e20610400aeb8bd30f122e7a146789abeac12d9492cb | 1 | 2026-07-27 14:30:31 | 1 |
| 11 | student10 | Student/Organizer | ladwarohit9@gmail.com | scrypt:32768:8:1$Wr2x1rhbOe6ieSN9$c04ea8fd6df83b73b0e8465247e84587f876778909f1401f41e731ecd279d5e4a1c1be3f35ff0705e93f4fd66293373a0c97a210b2f9e2e5af58bdd85e8b85e3 | 1 | 2026-07-31 04:43:18 | 1 |

## Table: `events`

| id | event_id | title | event_type | organizer_name | faculty_coordinator | contact_number | email | event_date | event_time | venue | budget | funding_source | expected_participants | chief_guest | objectives | description | schedule | required_resources | proposal_pdf_path | budget_pdf_path | supporting_docs_path | status | created_at | department_id | organizer_id | start_time | end_time | venue_id | post_event_report_path | reminder_sent | post_event_bill_path | event_category |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 38 | EVT-2026-001 | ai workshop | Department Level | student10 | kp sir | NULL | NULL | 2026-11-03 | NULL | Main Auditorium | 2000.0 | hod | 123 | asha mam | ok | ok | NULL | NULL | NULL | NULL | NULL | Approved | NULL | 1 | 11 | 10:00:00 | 12:00:00 | 1 | 38_report_certificate_36.pdf | NULL | 38_bill_certificate_36.pdf | Seminar/Workshop |
| 39 | EVT-2026-002 | open day | Department Level | student10 | asha mam  | NULL | NULL | 2026-10-18 | NULL | Main Auditorium | 2000.0 | college | 300 | kp sir | ok | ok | NULL | NULL | NULL | NULL | NULL | Approved | NULL | 1 | 11 | 10:00:00 | 12:00:00 | 1 | 39_report_38_bill_certificate_36_1.pdf | NULL | 39_bill_38_bill_certificate_36.pdf | Seminar/Workshop |
| 40 | EVT-2026-003 | workshop2 | Department Level | student10 | anusha mam | NULL | NULL | 2026-10-12 | NULL | Main Auditorium | 1290.0 | college | 234 | dd | ok | ok | NULL | NULL | NULL | NULL | NULL | Approved | NULL | 1 | 11 | 10:00:00 | 12:00:00 | 1 | 40_report_38_report_certificate_36_3.pdf | NULL | 40_bill_38_report_certificate_36_1.pdf | Seminar/Workshop |
| 41 | EVT-2026-004 | workshop3 | Department Level | student10 | kp sir | NULL | NULL | 2026-11-06 | NULL | Main Auditorium | 3000.0 | department | 300 | asha mam | ok | ok | NULL | NULL | NULL | NULL | NULL | Pending | NULL | 1 | 11 | 10:00:00 | 12:00:00 | 1 | NULL | NULL | NULL | Seminar/Workshop |
| 42 | EVT-2026-005 | open day | Department Level | student10 | kp sir | NULL | NULL | 2026-11-21 | NULL | Main Auditorium | 5000.0 | department | 300 | asha mam | ok | ok | NULL | NULL | NULL | NULL | NULL | Pending | NULL | 1 | 11 | 10:00:00 | 12:00:00 | 1 | NULL | NULL | NULL | Seminar/Workshop |
| 43 | EVT-2026-006 | ai tools | Department Level | student10 | kp sir | NULL | NULL | 2026-10-03 | NULL | Main Auditorium | 1234.0 | department | 450 | asha mam | ok | ok | NULL | NULL | NULL | NULL | NULL | Pending | NULL | 1 | 11 | 10:00:00 | 12:00:00 | 1 | NULL | NULL | NULL | Seminar/Workshop |
| 44 | EVT-2026-007 | mallika | Department Level | student10 | kp sir | NULL | NULL | 2026-12-05 | NULL | Main Auditorium | 1345.0 | department | 450 | asha mam | ok | ok | NULL | NULL | NULL | NULL | NULL | Pending | NULL | 1 | 11 | 10:00:00 | 12:00:00 | 1 | NULL | NULL | NULL | Seminar/Workshop |

## Table: `event_registrations`

| id | event_id | user_id | qr_token | attended | feedback_submitted | rating | feedback_text | created_at |
|---|---|---|---|---|---|---|---|---|
| 1 | 38 | 11 | 748b14d1-9ff1-4a75-9d7d-eb18bc0904e6 | 1 | 0 | NULL | NULL | 2026-07-31 16:21:23 |
| 2 | 39 | 11 | 768a8565-a661-46ea-9756-987017ddf958 | 1 | 1 | 5 | ok | 2026-07-31 16:35:41 |

## Table: `venues`

| id | name | capacity | type |
|---|---|---|---|
| 1 | Main Auditorium | 500 | Auditorium |
| 2 | Seminar Hall A | 100 | Seminar Hall |
| 3 | Seminar Hall B | 100 | Seminar Hall |
| 4 | CSE Lab 1 | 60 | Lab |
| 5 | ECE Lab 1 | 60 | Lab |
| 6 | Open Grounds | 1000 | Ground |

## Table: `departments`

| id | name | code |
|---|---|---|
| 1 | Computer Science and Engineering | CSE |
| 2 | Electronics and Communication Engineering | ECE |
| 3 | Mechanical Engineering | MECH |
| 4 | Civil Engineering | CIVIL |
| 5 | Electrical and Electronics Engineering | EEE |
| 6 | Information Technology | IT |
| 7 | Artificial Intelligence and Data Science | AIDS |
| 8 | Business Administration | BBA |

## Table: `approvals`

| id | status | comments | action_date | event_id | approver_id | required_role | level |
|---|---|---|---|---|---|---|---|
| 116 | Approved | ok | NULL | 38 | NULL | Faculty | 1 |
| 117 | Approved | ok | NULL | 38 | NULL | HOD | 2 |
| 118 | Approved | ok | NULL | 39 | NULL | Faculty | 1 |
| 119 | Approved | ok | NULL | 39 | NULL | HOD | 2 |
| 120 | Approved | ok | NULL | 40 | NULL | Faculty | 1 |
| 121 | Approved | ok | NULL | 40 | NULL | HOD | 2 |
| 122 | Pending | NULL | NULL | 41 | NULL | Faculty | 1 |
| 123 | Pending | NULL | NULL | 41 | NULL | HOD | 2 |
| 124 | Pending | NULL | NULL | 42 | NULL | Faculty | 1 |
| 125 | Pending | NULL | NULL | 42 | NULL | HOD | 2 |
| 126 | Pending | NULL | NULL | 43 | NULL | Faculty | 1 |
| 127 | Pending | NULL | NULL | 43 | NULL | HOD | 2 |
| 128 | Pending | NULL | NULL | 44 | NULL | Faculty | 1 |
| 129 | Pending | NULL | NULL | 44 | NULL | HOD | 2 |

## Table: `event_comments`

*Table is empty*

## Table: `notifications`

| id | message | is_read | created_at | link | user_id |
|---|---|---|---|---|---|
| 42 | Your event proposal 'mallika' has been submitted. | 0 | NULL | /events/44 | 11 |
| 43 | Event 'mallika' requires your approval. | 0 | NULL | /events/44 | 5 |

