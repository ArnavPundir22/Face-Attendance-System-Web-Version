# BioSecure AI — Standalone Developer License Kit

A self-contained, isolated developer toolkit for generating, issuing, inspecting, and managing cryptographically signed Ed25519 software licenses for the **BioSecure AI Face Attendance System**.

---

## 🔒 Security Architecture

- **Private Key (`developer_private_key.pem`)**:
  - Resides strictly in this `license_kit/` directory.
  - Set to restricted permissions (`chmod 600`).
  - **NEVER** commit this key to version control or copy it to customer host machines.
- **Public Key (`license_public_key.pem`)**:
  - Embedded into the application at `src/security/license_public_key.pem`.
  - Used by the server to verify digital signatures.
  - Cannot be used to forge or extend licenses.
- **Portability**:
  - You can zip this entire `license_kit/` folder and keep it on your personal computer or a secure USB drive, completely separate from the project repository.

---

## 🚀 How to Run the License Kit

### Linux / macOS
```bash
# Inside the license_kit folder:
./run_console.sh

# Or from project root:
./license_console.sh
```

### Windows
```cmd
# Double click or run:
run_console.bat
```

---

## 📋 Available Console Features

1. **Issue Client License Token (Interactive Wizard)**:
   - Enter client name (e.g. `ABC University`).
   - Choose duration preset (**7d**, **14d**, **30d**, **90d**, **365d**, custom days, or exact date).
   - Automatically signs the token with Ed25519 and saves it to `license_kit/output/`.
   - Offers to sync directly to the app root as `.license`.

2. **Inspect & Cryptographically Verify License**:
   - Validates any token's digital signature against the public key.
   - Shows remaining authorized days, client name, UUID, and expiration date.

3. **Generate / Rotate Keypair**:
   - Generates a new Ed25519 keypair and automatically updates the app's verification key.

4. **Security & Deployment Guide**:
   - Complete in-terminal documentation and deployment guidelines.

5. **System Diagnostics**:
   - Live checks of key files, file permissions, and active tokens.

---

## 📦 How to Deliver a License to a Client

1. Run the console: `./run_console.sh`
2. Select **[1] Issue Client License Token**.
3. Locate the generated `.license` file in `license_kit/output/`.
4. Send **ONLY** that `.license` file to the client.
5. On the host computer, place the file in the application root directory as `.license`.

---

## ⚙️ Dependencies

If running this kit on a separate machine without the project's virtual environment:
```bash
pip install -r requirements.txt
python license_console.py
```
*(Requires only Python 3.8+ and the standard `cryptography` package).*
