"""Crea un administrador pidiendo la clave por teclado (no queda en el código ni en GitHub)."""
import getpass

from database import usuarios


def main() -> None:
    usuario = input("Usuario del administrador: ")
    clave = getpass.getpass("Clave (mínimo 10 caracteres): ")
    if clave != getpass.getpass("Repite la clave: "):
        print("Las claves no coinciden.")
        return
    try:
        usuarios.crear_admin(usuario, clave)
    except ValueError as error:
        print(error)
        return
    print("Administrador creado.")


if __name__ == "__main__":
    main()
