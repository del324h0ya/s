"""
genertortoken.py — CLI token generator.

PENTING: token dibuat lewat script ini SEKARANG ditulis langsung ke
database yang sama dengan bot (table token_pool via database.py),
bukan lagi ke users.db terpisah. Sebelumnya token yang dibuat di sini
TIDAK PERNAH bisa diaktivasi user karena disimpan di DB & skema yang
berbeda dari yang dibaca bot.
"""

import secrets

import database


def generate_premium_token(days: int = 30) -> str | None:
    """Buat token unik, simpan hash-nya ke token_pool, kembalikan token mentah."""
    token = f"XAU-NEURAL-{secrets.token_hex(6).upper()}"

    database.init_db()  # pastikan tabel sudah ada
    success = database.add_token_to_pool(token, duration_days=days)

    if success:
        print(f"✅ Token Generated: {token}")
        print(f"📅 Duration: {days} hari")
        return token
    else:
        print("❌ Gagal menyimpan token (kemungkinan hash duplikat, coba lagi).")
        return None


if __name__ == "__main__":
    print("--- XORTRON TOKEN GENERATOR ---")
    days_input = input("Masukkan durasi aktif token (hari) [Default 30]: ")
    days = int(days_input) if days_input.isdigit() else 30

    new_token = generate_premium_token(days)
    if new_token:
        print("\nKirim token ini ke pembeli anda:\n")
        print(f"👉 {new_token} 👈")
