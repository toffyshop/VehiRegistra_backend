"""Mapeo de la respuesta del proveedor externo al schema interno.

El contrato exacto del proveedor todavía no está documentado (falta el token
para inspeccionar una respuesta real), así que el mapeo es tolerante a varias
formas posibles. Estas pruebas fijan ese comportamiento: cuando se consiga el
token y se conozca el JSON verdadero, basta añadir aquí ese caso.
"""

from app.services.sunarp_service import _mapear_respuesta


def test_mapea_una_respuesta_plana() -> None:
    record = _mapear_respuesta(
        {
            "marca": "bajaj",
            "modelo": "re 205 4t",
            "anio": "2021",
            "color": "azul",
            "numero_motor": "aembtg12345",
            "vin": "md2a11cz7mwa12345",
            "propietario": "juan carlos quispe mamani",
            "dni": "45781203",
        }
    )

    assert record is not None
    assert record["marca"] == "BAJAJ"
    assert record["modelo"] == "RE 205 4T"
    assert record["anio"] == 2021
    assert record["nro_motor"] == "AEMBTG12345"
    assert record["nro_serie"] == "MD2A11CZ7MWA12345"
    assert record["propietario"]["nombre_completo"] == "JUAN CARLOS QUISPE MAMANI"
    assert record["propietario"]["dni"] == "45781203"


def test_desenvuelve_la_envoltura_data_y_el_propietario_anidado() -> None:
    record = _mapear_respuesta(
        {
            "success": True,
            "data": {
                "brand": "HONDA",
                "model": "CG 125",
                "year": 2019,
                "propietario": {"nombre": "MARIA CONDORI", "documento": "42310998"},
            },
        }
    )

    assert record is not None
    assert record["marca"] == "HONDA"
    assert record["anio"] == 2019
    assert record["propietario"]["nombre_completo"] == "MARIA CONDORI"
    assert record["propietario"]["dni"] == "42310998"


def test_sin_datos_del_titular_no_inventa_propietario() -> None:
    record = _mapear_respuesta({"marca": "TVS", "modelo": "KING"})

    assert record is not None
    assert record["propietario"]["nombre_completo"] == "NO DISPONIBLE"
    assert record["propietario"]["dni"] == ""


def test_respuesta_inutil_se_descarta() -> None:
    """Sin marca ni modelo no se puede autocompletar: se trata como fallo."""
    assert _mapear_respuesta({"success": False, "message": "No encontrado"}) is None
    assert _mapear_respuesta({}) is None
    assert _mapear_respuesta("texto plano") is None


def test_anio_invalido_no_rompe_el_mapeo() -> None:
    record = _mapear_respuesta({"marca": "NISSAN", "modelo": "SENTRA", "anio": "s/d"})

    assert record is not None
    assert record["anio"] is None
