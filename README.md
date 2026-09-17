# SecurePaper - Secure Question Paper Management System

A secure web-based Question Paper Management System designed to protect examination papers throughout their lifecycle, from uploading and administrator approval to scheduled release and secure access by examination centres.

---

## Overview

SecurePaper is a Flask-based web application integrated with Supabase for authentication, database management, and secure file storage.

The system provides role-based access for three types of users:

- **Question Setter** - Uploads question papers securely.
- **Administrator** - Reviews and approves or rejects question papers.
- **Exam Centre** - Accesses approved papers only after their scheduled release time.

Question papers are encrypted before being stored, ensuring that the original PDF is not directly stored in the storage bucket.

---

## Key Features

### Authentication and Authorization

- User authentication using Supabase Auth
- Session-based access control
- Role-based authorization
- Separate access for Question Setters, Administrators, and Exam Centres

### Question Setter

- Upload question papers in PDF format
- Specify examination date
- Set a scheduled release time
- Encrypt uploaded papers automatically
- Generate SHA-256 hash for file integrity
- Track the approval status of uploaded papers

### Administrator

- View uploaded question papers
- Review pending submissions
- Approve question papers
- Reject question papers

### Exam Centre

- View approved question papers
- Check paper release status
- Access papers only after the scheduled release time
- View the decrypted PDF securely

### Encryption

Question papers are encrypted using Fernet symmetric encryption before being stored.

```text
Original PDF
     |
     v
SHA-256 Hash
     |
     v
Fernet Encryption
     |
     v
Encrypted .enc File
     |
     v
Supabase Storage
