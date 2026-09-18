import os
import sys
import csv
from datetime import datetime
import threading


def resource_path(relative_path):
    """Obtiene la ruta absoluta al recurso, funciona tanto en desarrollo
    como cuando está empaquetado con PyInstaller (.exe)."""
    if hasattr(sys, '_MEIPASS'):
        # Ruta temporal donde PyInstaller desempaqueta los archivos
        return os.path.join(sys._MEIPASS, relative_path)
    # En desarrollo: relativo al directorio del script
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)

from fpdf import FPDF
from kivy.properties import StringProperty, NumericProperty, ObjectProperty, ListProperty
from kivy.uix.widget import Widget
from kivy.graphics import Color, Line, Ellipse, Rectangle
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.card import MDCard
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton, MDRaisedButton, MDIconButton
from kivymd.uix.behaviors import HoverBehavior
from kivy.animation import Animation
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.snackbar import MDSnackbar
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.lang import Builder

from database import (
    iniciar_db, obtener_productos, obtener_producto_por_id,
    obtener_producto_por_codigo_barras,
    insertar_producto, actualizar_producto, eliminar_producto,
    actualizar_stock, registrar_venta, obtener_ventas,
    obtener_estadisticas, obtener_ventas_por_producto,
    obtener_ventas_por_categoria, obtener_ventas_diarias,
    obtener_ventas_para_exportar, obtener_config, guardar_config
)
from theme import (
    VERDE_PRINCIPAL, VERDE_CLARO, VERDE_SUAVE, VERDE_OSCURO,
    MORADO, MORADO_SUAVE, AZUL, AZUL_SUAVE,
    NARANJA, NARANJA_SUAVE, ROJO, AMARILLO,
    AMARILLO_SUAVE, GRIS_MEDIO, GRIS_TEXTO, BLANCO, FONDO, COLORES_BARRA
)


from kivy.properties import StringProperty, NumericProperty, ObjectProperty, ListProperty, BooleanProperty, ColorProperty

class HoverIconButton(MDIconButton, HoverBehavior):
    hover_bg = ListProperty([0, 0, 0, 0])
    hover = BooleanProperty(False)

    def on_enter(self, *args):
        self.hover = True

    def on_leave(self, *args):
        self.hover = False

class ItemProducto(MDCard):
    id_producto = NumericProperty()
    nombre = StringProperty()
    precio = NumericProperty()
    stock = NumericProperty()
    fecha_registro = StringProperty("")
    categoria = StringProperty("General")
    codigo_barras = StringProperty("")
    screen = ObjectProperty()
    anim_delay = NumericProperty(0)

    def on_kv_post(self, base_widget):
        if self.anim_delay < 0:
            # Sin animación – aparecer de inmediato
            self.opacity = 1
            self.elevation = 2
            return
        self.opacity = 0
        self.elevation = 0
        anim = Animation(opacity=1, elevation=2, d=0.3, t='out_quad')
        if self.anim_delay > 0:
            anim = Animation(d=self.anim_delay) + anim
        anim.start(self)


class ContenidoEdicionDialog(MDBoxLayout):
    nombre = StringProperty()
    precio = StringProperty()
    stock = StringProperty()
    categoria = StringProperty("General")
    codigo_barras = StringProperty("")


class ContenidoAgregarStockDialog(MDBoxLayout):
    pass


class ItemVenta(MDCard):
    nombre_producto = StringProperty()
    cantidad = NumericProperty()
    total = NumericProperty()
    fecha = StringProperty()


class BarraGrafico(MDBoxLayout):
    valor_formateado = StringProperty()
    nombre = StringProperty()
    size_hint_bar = NumericProperty(0.1)
    indice = NumericProperty(0)


class GraficoLineas(Widget):
    datos = ListProperty([])
    etiquetas_x = ListProperty([])
    animating = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(size=self.dibujar, pos=self.dibujar)
        self.scale_factor = 0

    def on_datos(self, *args):
        self.animar_entrada()

    def animar_entrada(self):
        self.scale_factor = 0
        self.animating = True
        anim = Animation(scale_factor=1, d=0.6, t='out_quad')
        anim.bind(on_complete=self.on_anim_complete)
        anim.start(self)

    def on_anim_complete(self, *args):
        self.animating = False

    def on_scale_factor(self, *args):
        self.dibujar()

    def dibujar(self, *args):
        self.canvas.clear()
        if not self.datos:
            return
        with self.canvas:
            padding_x = 50
            padding_y = 40
            w = self.width - 2 * padding_x
            h = self.height - 2 * padding_y
            max_val = max(self.datos) if self.datos else 1
            if max_val == 0:
                max_val = 1
            n = len(self.datos)
            if n < 2:
                x_coords = [self.x + padding_x + w / 2]
                y_coords = [self.y + padding_y + (self.datos[0] / max_val) * h * self.scale_factor]
            else:
                x_coords = [self.x + padding_x + (i / (n - 1)) * w for i in range(n)]
                y_coords = [self.y + padding_y + (val / max_val) * h * self.scale_factor for val in self.datos]
            
            # Fondo claro para el área del gráfico
            Color(1, 1, 1, 1)
            Rectangle(pos=(self.x + padding_x, self.y + padding_y), size=(w, h))
            
            # Líneas de grid con color gris claro
            Color(0.4, 0.45, 0.5, 0.3)
            for i in range(5):
                y_line = self.y + padding_y + (i / 4) * h
                Line(points=[self.x + padding_x, y_line, self.x + padding_x + w, y_line], width=1)
            
            # Líneas verticales de grid
            for i in range(n):
                x_line = self.x + padding_x + (i / max(1, n - 1)) * w
                Line(points=[x_line, self.y + padding_y, x_line, self.y + padding_y + h], width=0.5)
            
            # Gradiente para el área bajo la línea
            if len(self.datos) >= 2:
                # Crear gradiente vertical
                Color(*VERDE_PRINCIPAL)
                points_area = [x_coords[0], self.y + padding_y]
                for x, y in zip(x_coords, y_coords):
                    points_area.extend([x, y])
                points_area.extend([x_coords[-1], self.y + padding_y])
                Line(points=points_area, width=0, close=True)
            
            # Línea principal con gradiente de color
            Color(*VERDE_CLARO)
            if len(self.datos) >= 2:
                points = []
                for x, y in zip(x_coords, y_coords):
                    points.extend([x, y])
                Line(points=points, width=3)
            
            # Puntos de datos con efecto de brillo
            for i, (x, y) in enumerate(zip(x_coords, y_coords)):
                # Círculo exterior con transparencia
                Color(*VERDE_PRINCIPAL[0:3] + (0.3,))
                Ellipse(pos=(x - 8, y - 8), size=(16, 16))
                # Círculo principal
                Color(*VERDE_PRINCIPAL)
                Ellipse(pos=(x - 5, y - 5), size=(10, 10))
                # Centro blanco
                Color(1, 1, 1, 1)
                Ellipse(pos=(x - 2, y - 2), size=(4, 4))


class PantallaInventario(MDScreen):
    dialogo_edicion = None
    dialogo_confirmacion = None
    menu_productos = None
    producto_seleccionado_id = None
    _filtro_event = None  # Para debounce del buscador
    _datos_cargados = False

    def on_enter(self, *args):
        # Diferir la carga al siguiente frame para que la pantalla se renderice primero
        if not self._datos_cargados:
            Clock.schedule_once(self._cargar_inicial, 0)
            self._datos_cargados = True
        else:
            Clock.schedule_once(lambda dt: self.cargar_productos(), 0)

    def _cargar_inicial(self, dt):
        self.cargar_productos()
        self.cargar_ventas()

    def mostrar_alerta(self, mensaje, tipo="exito"):
        if tipo == "exito":
            bg_color = list(VERDE_PRINCIPAL)
            prefix = "✓ "
        elif tipo == "error":
            bg_color = list(ROJO)
            prefix = "❌ "
        else:
            bg_color = list(AMARILLO)
            prefix = "⚠ "
            
        texto = f"{prefix}{mensaje}" if not mensaje.startswith(('✓', '❌', '⚠')) else mensaje
        
        MDSnackbar(
            MDLabel(text=texto, theme_text_color="Custom", text_color=[1, 1, 1, 1], bold=True),
            md_bg_color=bg_color,
            duration=2.5,
            pos_hint={"center_x": 0.5},
            size_hint_x=0.5
        ).open()

    # ─────────────────────────────────────────────────────────────────────────
    # LECTOR DE CÓDIGO DE BARRAS – REGISTRO
    # El lector actúa como teclado: escribe el código y envía Enter.
    # on_text_validate del campo codigo_barras en la pantalla de Registro.
    # ─────────────────────────────────────────────────────────────────────────
    def codigo_barras_registrado(self, codigo_texto):
        """Llamado cuando el lector escanea en la pantalla de Registro.
        Verifica si el código ya existe en BD; si es así, avisa.
        Luego mueve el foco al campo de nombre."""
        codigo = codigo_texto.strip()
        if not codigo:
            return
        existente = obtener_producto_por_codigo_barras(codigo)
        if existente:
            self.mostrar_alerta(
                f"⚠ Código ya asignado a: {existente['nombre']}", tipo="error"
            )
        else:
            self.mostrar_alerta(f"Código leído: {codigo}")
        # Mover foco al campo Nombre
        self.ids.input_nombre.focus = True

    # ─────────────────────────────────────────────────────────────────────────
    # LECTOR DE CÓDIGO DE BARRAS – BÚSQUEDA (tab Inventario)
    # ─────────────────────────────────────────────────────────────────────────
    def buscar_por_codigo_barras(self, codigo_texto):
        """Llamado cuando el lector presiona Enter en el campo de búsqueda.
        Busca el producto con coincidencia EXACTA en codigo_barras."""
        codigo = codigo_texto.strip()
        if not codigo:
            return
        prod = obtener_producto_por_codigo_barras(codigo)
        if prod:
            # Muestra solo ese producto en la lista
            self.ids.lista_productos.clear_widgets()
            id_p, nombre, precio, stock = prod["id"], prod["nombre"], prod["precio"], prod["stock"]
            tarjeta = ItemProducto(
                id_producto=id_p, nombre=nombre, precio=precio,
                stock=stock, fecha_registro="",
                categoria="General", codigo_barras=codigo, screen=self,
                anim_delay=0.1
            )
            self.ids.lista_productos.add_widget(tarjeta)
            self.ids.label_total_productos.text = "1"
            self.mostrar_alerta(f"Producto encontrado: {nombre}")
        else:
            self.mostrar_alerta(f"No se encontró producto con código: {codigo}", tipo="error")
            # Hace búsqueda de texto normal como fallback
            self.cargar_productos(codigo)

    # ─────────────────────────────────────────────────────────────────────────
    # LECTOR DE CÓDIGO DE BARRAS – VENTAS
    # ─────────────────────────────────────────────────────────────────────────
    def codigo_barras_venta(self, codigo_texto):
        """Llamado cuando el lector escanea en la pantalla de Ventas.
        Busca el producto y lo selecciona automáticamente para la venta."""
        codigo = codigo_texto.strip()
        if not codigo:
            return
        prod = obtener_producto_por_codigo_barras(codigo)
        if prod:
            # Convierte Row a tupla compatible con seleccionar_producto_venta
            # Row tiene: id, nombre, precio, stock
            self.producto_seleccionado_id = prod["id"]
            self.ids.input_producto_venta.text = prod["nombre"]
            self.ids.label_precio_unitario.text = (
                f"Precio: ${prod['precio']:,.2f}  |  Stock: {prod['stock']}"
            )
            # Limpia el campo del código y mueve foco a cantidad
            self.ids.input_codigo_venta.text = ""
            self.ids.input_cantidad_venta.focus = True
            self.mostrar_alerta(f"✓ {prod['nombre']} seleccionado")
        else:
            self.ids.input_codigo_venta.text = ""
            self.mostrar_alerta(f"Producto no encontrado: {codigo}", tipo="error")

    # ─────────────────────────────────────────────────────────────────────────
    # REGISTRO DE PRODUCTO
    # ─────────────────────────────────────────────────────────────────────────
    def guardar_producto(self, nombre, precio, stock, categoria="General", codigo_barras=""):
        if nombre.strip() == "" or precio.strip() == "" or stock.strip() == "":
            self.mostrar_alerta("Llena todos los campos obligatorios.", tipo="error")
            return
        try:
            cb = codigo_barras.strip() or None
            insertar_producto(nombre.strip(), float(precio), int(stock), categoria.strip() or "General", cb)
            self.ids.input_codigo_barras.text = ""
            self.ids.input_nombre.text = ""
            self.ids.input_precio.text = ""
            self.ids.input_stock.text = ""
            self.ids.input_categoria.text = ""
            self.mostrar_alerta(f"{nombre} guardado con éxito.")
            self.cargar_productos()
        except ValueError:
            self.mostrar_alerta("Precio y Stock deben ser números.", tipo="error")

    def cargar_productos(self, filtro=""):
        self.ids.lista_productos.clear_widgets()
        productos = obtener_productos(filtro)
        valor_total = 0.0
        
        MAX_ANIMADOS = 8  # Solo animar las primeras N tarjetas
        widgets = []
        for i, prod in enumerate(productos):
            id_p, nombre, precio, stock, fecha_reg, categoria, codigo_barras = prod
            valor_total += precio * stock
            tarjeta = ItemProducto(
                id_producto=id_p, nombre=nombre, precio=precio,
                stock=stock, fecha_registro=fecha_reg or "Sin fecha",
                categoria=categoria or "General",
                codigo_barras=codigo_barras or "",
                screen=self,
                anim_delay=i * 0.04 if i < MAX_ANIMADOS else -1
            )
            widgets.append(tarjeta)

        # Insertar en lotes para no congelar la UI
        BATCH = 20
        lista = self.ids.lista_productos
        
        def _agregar_lote(dt, inicio=0):
            fin = min(inicio + BATCH, len(widgets))
            for j in range(inicio, fin):
                lista.add_widget(widgets[j])
            if fin < len(widgets):
                Clock.schedule_once(lambda dt: _agregar_lote(dt, fin), 0)

        if widgets:
            _agregar_lote(None)

        self.ids.label_total_productos.text = str(len(productos))
        self.ids.label_valor_total.text = f"${valor_total:,.2f}"

    def filtrar_productos(self, texto):
        # Debounce: esperar 300ms después de la última tecla antes de filtrar
        if self._filtro_event:
            self._filtro_event.cancel()
        self._filtro_event = Clock.schedule_once(lambda dt: self.cargar_productos(texto), 0.3)

    def agregar_stock_dialog(self, item_widget):
        contenido = ContenidoAgregarStockDialog()
        self.dialogo_edicion = MDDialog(
            title=f"Agregar stock a {item_widget.nombre}",
            type="custom",
            content_cls=contenido,
            buttons=[
                MDFlatButton(text="CANCELAR", theme_text_color="Custom", text_color=list(VERDE_PRINCIPAL), on_release=lambda x: self.dialogo_edicion.dismiss()),
                MDRaisedButton(text="AGREGAR", md_bg_color=list(VERDE_PRINCIPAL), on_release=lambda x: self.guardar_stock(item_widget, contenido.ids.add_stock.text)),
            ],
        )
        self.dialogo_edicion.open()

    def guardar_stock(self, item_widget, stock_a_agregar):
        if stock_a_agregar.strip() == "":
            self.mostrar_alerta("Ingresa una cantidad.", tipo="error")
            return
        try:
            stock_nuevo = item_widget.stock + int(stock_a_agregar)
            actualizar_stock(item_widget.id_producto, stock_nuevo)
            self.dialogo_edicion.dismiss()
            self.mostrar_alerta(f"Stock: {stock_nuevo}")
            self.cargar_productos(self.ids.input_busqueda.text)
        except ValueError:
            self.mostrar_alerta("Debes ingresar un número válido.", tipo="error")

    def editar_producto_dialog(self, item_widget):
        contenido = ContenidoEdicionDialog(
            nombre=item_widget.nombre, precio=str(item_widget.precio),
            stock=str(item_widget.stock), categoria=item_widget.categoria,
            codigo_barras=item_widget.codigo_barras or ""
        )
        self.dialogo_edicion = MDDialog(
            title="Editar Producto", type="custom", content_cls=contenido,
            buttons=[
                MDFlatButton(text="CANCELAR", theme_text_color="Custom", text_color=list(VERDE_PRINCIPAL), on_release=lambda x: self.dialogo_edicion.dismiss()),
                MDRaisedButton(text="GUARDAR", md_bg_color=list(VERDE_PRINCIPAL), on_release=lambda x: self.guardar_cambios_edicion(
                    item_widget.id_producto,
                    contenido.ids.edit_nombre.text,
                    contenido.ids.edit_precio.text,
                    contenido.ids.edit_stock.text,
                    contenido.ids.edit_categoria.text,
                    contenido.ids.edit_codigo_barras.text)),
            ],
        )
        self.dialogo_edicion.open()

    def guardar_cambios_edicion(self, id_producto, nombre, precio, stock, categoria="General", codigo_barras=""):
        if nombre.strip() == "" or precio.strip() == "" or stock.strip() == "":
            self.mostrar_alerta("Los campos obligatorios no pueden estar vacíos.", tipo="error")
            return
        try:
            actualizar_producto(id_producto, nombre.strip(), float(precio), int(stock), categoria.strip() or "General", codigo_barras.strip() or None)
            self.dialogo_edicion.dismiss()
            self.mostrar_alerta("Producto actualizado.")
            self.cargar_productos(self.ids.input_busqueda.text)
        except ValueError:
            self.mostrar_alerta("Precio y Stock deben ser números.", tipo="error")

    def confirmar_eliminar(self, item_widget):
        self.dialogo_confirmacion = MDDialog(
            title="Eliminar producto",
            text=f"Eliminar '{item_widget.nombre}'? Esta acción no se puede deshacer.",
            buttons=[
                MDFlatButton(text="CANCELAR", theme_text_color="Custom", text_color=list(VERDE_PRINCIPAL), on_release=lambda x: self.dialogo_confirmacion.dismiss()),
                MDRaisedButton(text="ELIMINAR", md_bg_color=list(ROJO), on_release=lambda x: self.ejecutar_eliminacion(item_widget.id_producto)),
            ],
        )
        self.dialogo_confirmacion.open()

    def ejecutar_eliminacion(self, id_producto):
        eliminar_producto(id_producto)
        self.dialogo_confirmacion.dismiss()
        self.mostrar_alerta("Producto eliminado.")
        self.cargar_productos(self.ids.input_busqueda.text)

    def abrir_menu_productos(self, caller_widget):
        productos = obtener_productos()
        if not productos:
            self.mostrar_alerta("No hay productos en inventario.", tipo="error")
            return
        menu_items = []
        for prod in productos:
            id_p, nombre, precio, stock, _, _, _ = prod
            menu_items.append({
                "viewclass": "OneLineListItem",
                "text": f"{nombre}  (Stock: {stock})",
                "on_release": lambda x=prod: self.seleccionar_producto_venta(x),
            })
        self.menu_productos = MDDropdownMenu(caller=caller_widget, items=menu_items, width_mult=4)
        self.menu_productos.open()

    def seleccionar_producto_venta(self, prod):
        self.producto_seleccionado_id = prod[0]
        self.ids.input_producto_venta.text = prod[1]
        self.ids.label_precio_unitario.text = f"Precio: ${prod[2]:,.2f}  |  Stock: {prod[3]}"
        if self.menu_productos:
            self.menu_productos.dismiss()

    def registrar_venta(self, cantidad_texto):
        if not self.producto_seleccionado_id:
            self.mostrar_alerta("Selecciona un producto.", tipo="error")
            return
        if cantidad_texto.strip() == "":
            self.mostrar_alerta("Ingresa la cantidad.", tipo="error")
            return
        metodo_pago = self.ids.input_metodo_pago.text.strip() or "Efectivo"
        try:
            cantidad = int(cantidad_texto)
            if cantidad <= 0:
                self.mostrar_alerta("La cantidad debe ser mayor que cero.", tipo="error")
                return
            prod = obtener_producto_por_id(self.producto_seleccionado_id)
            if not prod:
                self.mostrar_alerta("Producto no encontrado.", tipo="error")
                return
            nombre, precio, stock_actual = prod
            if stock_actual < cantidad:
                self.mostrar_alerta(f"Stock insuficiente. Quedan {stock_actual} unidades.", tipo="error")
                return
            total = precio * cantidad
            if registrar_venta(self.producto_seleccionado_id, cantidad, total, metodo_pago):
                self.mostrar_alerta(f"Venta de {nombre} por ${total:,.2f} ({metodo_pago})")
                self.ids.input_codigo_venta.text = ""
                self.ids.input_producto_venta.text = ""
                self.ids.input_cantidad_venta.text = ""
                self.ids.input_metodo_pago.text = "Efectivo"
                self.ids.label_precio_unitario.text = "Selecciona un producto..."
                self.producto_seleccionado_id = None
                self.cargar_productos()
                self.cargar_ventas()
            else:
                self.mostrar_alerta("Error al procesar la venta.", tipo="error")
        except ValueError:
            self.mostrar_alerta("La cantidad debe ser un número entero.", tipo="error")

    def recargar_todo(self):
        """Recarga todos los datos de la aplicación de una sola vez."""
        self.cargar_productos()
        self.cargar_ventas()
        self.cargar_reportes()
        
        # Actualizar título basado en la pestaña actual
        app = MDApp.get_running_app()
        if 'bottom_nav' in self.ids:
            current_tab = self.ids.bottom_nav.current
            tab_names = {
                'tab_inventario': 'Inventario',
                'tab_registrar': 'Registrar',
                'tab_ventas': 'Ventas',
                'tab_reportes': 'Reportes'
            }
            if current_tab in tab_names:
                self.ids.top_bar.title = f"{app.title} - {tab_names[current_tab]}"
            else:
                self.ids.top_bar.title = app.title
        else:
            self.ids.top_bar.title = app.title
            
        self.mostrar_alerta("Datos actualizados", tipo="success")

    def cargar_ventas(self):
        def _consultar_ventas():
            return obtener_ventas()

        def _actualizar_ui_ventas(ventas):
            try:
                self.ids.lista_ventas.clear_widgets()
                total_acumulado = 0.0
                widgets = []
                for v in ventas:
                    _, nombre_prod, cant, total, fecha = v
                    total_acumulado += total
                    item = ItemVenta(nombre_producto=nombre_prod, cantidad=cant, total=total, fecha=fecha)
                    widgets.append(item)

                BATCH = 25
                lista = self.ids.lista_ventas

                def _agregar_lote(dt, inicio=0):
                    fin = min(inicio + BATCH, len(widgets))
                    for j in range(inicio, fin):
                        lista.add_widget(widgets[j])
                    if fin < len(widgets):
                        Clock.schedule_once(lambda dt: _agregar_lote(dt, fin), 0)
                    else:
                        Clock.schedule_once(lambda dt: setattr(lista, 'height', lista.minimum_height), 0)

                if widgets:
                    _agregar_lote(None)
                else:
                    self.ids.lista_ventas.add_widget(
                        MDLabel(text="No hay ventas registradas", halign="center", theme_text_color="Secondary")
                    )

                self.ids.label_total_ventas.text = f"${total_acumulado:,.2f}"
            except Exception as e:
                self.mostrar_alerta(f"Error al cargar ventas: {e}", tipo="error")

        def _hilo():
            ventas = _consultar_ventas()
            Clock.schedule_once(lambda dt: _actualizar_ui_ventas(ventas), 0)

        threading.Thread(target=_hilo, daemon=True).start()

    def cargar_reportes(self):
        def cargar_datos_async():
            stats = obtener_estadisticas()
            ventas_por_prod = obtener_ventas_por_producto()
            ventas_por_cat = obtener_ventas_por_categoria()
            ventas_diarias = obtener_ventas_diarias()
            
            Clock.schedule_once(lambda dt: self.actualizar_ui_reportes(stats, ventas_por_prod, ventas_por_cat, ventas_diarias), 0)
        
        threading.Thread(target=cargar_datos_async, daemon=True).start()

    def mostrar_productos_mas_vendidos(self):
        try:
            ventas_por_prod = obtener_ventas_por_producto(limite=20)
            print(f"Ventas por producto: {ventas_por_prod}")
            
            if not ventas_por_prod:
                self.mostrar_alerta("No hay ventas registradas", tipo="error")
                return
            
            # Convertir objetos Row a tuplas
            ventas_por_prod = [(row[0], row[1]) for row in ventas_por_prod]
            print(f"Ventas convertidas: {ventas_por_prod}")
            
            # Crear texto con formato simple
            texto = ""
            for i, (nombre, total) in enumerate(ventas_por_prod, 1):
                texto += f"{i}. {nombre} - ${total:,.2f}\n"
            
            self.dialogo_productos = MDDialog(
                title="Ranking de Productos",
                text=texto,
                buttons=[
                    MDFlatButton(text="CERRAR", theme_text_color="Custom", text_color=list(VERDE_PRINCIPAL), on_release=lambda x: self.dialogo_productos.dismiss())
                ]
            )
            self.dialogo_productos.open()
        except Exception as e:
            print(f"Error al mostrar productos más vendidos: {e}")
            self.mostrar_alerta(f"Error: {e}", tipo="error")

    def actualizar_ui_reportes(self, stats, ventas_por_prod, ventas_por_cat, ventas_diarias):
        self.ids.label_reportes_ingresos.text = f"${stats['total_ingresos']:,.2f}"
        self.ids.label_reportes_unidades.text = str(stats['total_unidades'])
        self.ids.label_reportes_transacciones.text = str(stats['total_transacciones'])
        self.ids.label_reportes_ganancias.text = f"${stats['ganancia_estimada']:,.2f}"
        
        self.ids.contenedor_grafico.clear_widgets()
        if ventas_por_prod:
            self.ids.label_producto_estrella.text = f"{ventas_por_prod[0][0]}  (${ventas_por_prod[0][1]:,.2f})"
        else:
            self.ids.label_producto_estrella.text = "Sin datos"
        
        if not ventas_por_prod:
            self.ids.contenedor_grafico.add_widget(MDLabel(text="Registra ventas para ver el gráfico", halign="center", theme_text_color="Custom", text_color=(0.3, 0.3, 0.3, 1)))
        else:
            max_venta = max(x[1] for x in ventas_por_prod) or 1
            for i, (nombre, total_venta) in enumerate(ventas_por_prod):
                barra = BarraGrafico(nombre=nombre, valor_formateado=f"${total_venta:,.0f}", size_hint_bar=max(0.1, total_venta / max_venta), indice=i)
                barra.opacity = 0
                self.ids.contenedor_grafico.add_widget(barra)
                anim = Animation(opacity=1, d=0.3, t='out_quad')
                anim.start(barra)
        
        self.ids.contenedor_grafico_categorias.clear_widgets()
        if not ventas_por_cat:
            self.ids.contenedor_grafico_categorias.add_widget(MDLabel(text="Registra ventas para ver categorías", halign="center", theme_text_color="Custom", text_color=(0.3, 0.3, 0.3, 1)))
        else:
            max_cat = max(x[1] for x in ventas_por_cat) or 1
            for i, (nombre_cat, total_cat) in enumerate(ventas_por_cat):
                barra = BarraGrafico(nombre=nombre_cat, valor_formateado=f"${total_cat:,.0f}", size_hint_bar=max(0.1, total_cat / max_cat), indice=i)
                barra.opacity = 0
                self.ids.contenedor_grafico_categorias.add_widget(barra)
                anim = Animation(opacity=1, d=0.3, t='out_quad')
                anim.start(barra)
        
        ventas_diarias = obtener_ventas_diarias()
        self.ids.grafico_lineas.datos = [x[1] for x in ventas_diarias] if ventas_diarias else []

    def _exportar_csv(self, titulo, nombre_archivo, encabezados, datos, codificacion="utf-8"):
        from tkinter import Tk, filedialog
        root = Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        ruta = filedialog.asksaveasfilename(title=titulo, defaultextension=".csv", filetypes=[("CSV", "*.csv")], initialfile=nombre_archivo)
        root.destroy()
        if not ruta:
            return
        try:
            with open(ruta, "w", newline="", encoding=codificacion) as f:
                writer = csv.writer(f)
                writer.writerow(encabezados)
                writer.writerows(datos)
            self.mostrar_alerta(f"Archivo: {os.path.basename(ruta)}")
            return True
        except Exception as e:
            self.mostrar_alerta(f"Error: {e}", tipo="error")
            return False

    def exportar_ventas_csv(self):
        datos = obtener_ventas_para_exportar()
        if not datos:
            self.mostrar_alerta("No hay ventas para exportar.", tipo="error")
            return
        if self._exportar_csv("Exportar ventas CSV", "reporte_ventas.csv", ["N", "Producto", "Categoría", "Cantidad", "Total ($)", "Fecha", "Método Pago"], datos):
            MDApp.get_running_app().ventas_exportadas = True

    def exportar_ventas_excel(self):
        datos = obtener_ventas_para_exportar()
        if not datos:
            self.mostrar_alerta("No hay ventas para exportar.", tipo="error")
            return
        if self._exportar_csv("Exportar ventas Excel", "reporte_ventas.csv", ["N", "Producto", "Categoría", "Cantidad", "Total ($)", "Fecha", "Método Pago"], datos, codificacion="utf-8-sig"):
            MDApp.get_running_app().ventas_exportadas = True

    def exportar_ventas_pdf(self):
        ventas = obtener_ventas_para_exportar()
        if not ventas:
            self.mostrar_alerta("No hay ventas para exportar.", tipo="error")
            return
        from tkinter import Tk, filedialog
        root = Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        ruta = filedialog.asksaveasfilename(title="Exportar ventas PDF", defaultextension=".pdf", filetypes=[("PDF", "*.pdf")], initialfile="reporte_ventas.pdf")
        root.destroy()
        if not ruta:
            return
        try:
            stats = obtener_estadisticas()
            pdf = FPDF()
            pdf.add_page()
            pdf.set_fill_color(*[int(c*255) for c in VERDE_OSCURO[:3]])
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Arial", 'B', 18)
            pdf.cell(0, 14, "REPORTE DE VENTAS", ln=True, align="C", fill=True)
            pdf.set_text_color(80, 80, 80)
            pdf.set_font("Arial", size=10)
            pdf.cell(0, 8, f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align="C")
            pdf.ln(6)
            pdf.set_fill_color(240, 248, 243)
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Arial", 'B', 11)
            for col, w in [("#", 10), ("Producto", 55), ("Cantidad", 20), ("Total", 30), ("Fecha", 40), ("Método", 30)]:
                pdf.cell(w, 9, col, border=1, align="C", fill=True)
            pdf.ln()
            pdf.set_font("Arial", size=10)
            for i, (vid, nombre, _, cant, total, fecha, metodo_pago) in enumerate(ventas):
                fill = (i % 2 == 0)
                if fill: pdf.set_fill_color(250, 250, 250)
                else: pdf.set_fill_color(255, 255, 255)
                pdf.cell(10, 8, str(vid), border=1, fill=fill)
                pdf.cell(55, 8, nombre[:25], border=1, fill=fill)
                pdf.cell(20, 8, str(cant), border=1, align="C", fill=fill)
                pdf.cell(30, 8, f"${total:,.2f}", border=1, align="R", fill=fill)
                pdf.cell(40, 8, fecha[:16] if fecha else "-", border=1, align="C", fill=fill)
                pdf.cell(30, 8, metodo_pago[:12] if metodo_pago else "-", border=1, align="C", fill=fill)
                pdf.ln()
            pdf.ln(4)
            pdf.set_font("Arial", 'B', 12)
            pdf.set_fill_color(*[int(c*255) for c in VERDE_PRINCIPAL[:3]])
            pdf.set_text_color(255, 255, 255)
            pdf.cell(0, 10, f"TOTAL: ${stats['total_ingresos']:,.2f}", ln=True, align="R", fill=True)
            pdf.output(ruta)
            MDApp.get_running_app().ventas_exportadas = True
            self.mostrar_alerta("PDF generado.")
        except Exception as e:
            self.mostrar_alerta(f"Error: {e}", tipo="error")

    def exportar_inventario_csv(self):
        productos = obtener_productos()
        if not productos:
            self.mostrar_alerta("No hay productos.", tipo="error")
            return
        self._exportar_csv("Exportar inventario CSV", "reporte_inventario.csv", ["ID", "Nombre", "Precio", "Stock", "Fecha Registro", "Categoria", "Código Barras"], productos)

    def exportar_inventario_excel(self):
        productos = obtener_productos()
        if not productos:
            self.mostrar_alerta("No hay productos.", tipo="error")
            return
        self._exportar_csv("Exportar inventario Excel", "reporte_inventario.csv", ["ID", "Nombre", "Precio", "Stock", "Fecha Registro", "Categoria", "Código Barras"], productos, codificacion="utf-8-sig")

    def exportar_inventario_pdf(self):
        productos = obtener_productos()
        if not productos:
            self.mostrar_alerta("No hay productos.", tipo="error")
            return
        from tkinter import Tk, filedialog
        root = Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        ruta = filedialog.asksaveasfilename(title="Exportar inventario PDF", defaultextension=".pdf", filetypes=[("PDF", "*.pdf")], initialfile="reporte_inventario.pdf")
        root.destroy()
        if not ruta:
            return
        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_fill_color(*[int(c*255) for c in VERDE_OSCURO[:3]])
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Arial", 'B', 18)
            pdf.cell(0, 14, "REPORTE DE INVENTARIO", ln=True, align="C", fill=True)
            pdf.set_text_color(80, 80, 80)
            pdf.set_font("Arial", size=10)
            pdf.cell(0, 8, f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align="C")
            pdf.ln(6)
            pdf.set_fill_color(240, 248, 243)
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Arial", 'B', 10)
            for col, w in [("ID", 10), ("Nombre", 55), ("Categoria", 30), ("Precio", 30), ("Stock", 20), ("Fecha", 45)]:
                pdf.cell(w, 9, col, border=1, align="C", fill=True)
            pdf.ln()
            pdf.set_font("Arial", size=9)
            valor_total = 0
            for i, (pid, nombre, precio, stock, fecha, cat, _) in enumerate(productos):
                valor_total += precio * stock
                fill = (i % 2 == 0)
                if fill: pdf.set_fill_color(250, 250, 250)
                else: pdf.set_fill_color(255, 255, 255)
                pdf.cell(10, 8, str(pid), border=1, fill=fill)
                pdf.cell(55, 8, nombre[:25], border=1, fill=fill)
                pdf.cell(30, 8, cat[:15] if cat else "-", border=1, fill=fill)
                pdf.cell(30, 8, f"${precio:,.2f}", border=1, align="R", fill=fill)
                pdf.cell(20, 8, str(stock), border=1, align="C", fill=fill)
                pdf.cell(45, 8, fecha[:19] if fecha else "-", border=1, align="C", fill=fill)
                pdf.ln()
            pdf.ln(4)
            pdf.set_font("Arial", 'B', 12)
            pdf.set_fill_color(*[int(c*255) for c in VERDE_PRINCIPAL[:3]])
            pdf.set_text_color(255, 255, 255)
            pdf.cell(0, 10, f"VALOR TOTAL: ${valor_total:,.2f}", ln=True, align="R", fill=True)
            pdf.output(ruta)
            self.mostrar_alerta("PDF generado.")
        except Exception as e:
            self.mostrar_alerta(f"Error: {e}", tipo="error")


class PantallaConfiguracion(MDScreen):
    def on_enter(self):
        config = obtener_config()
        if config:
            try:
                self.ids.input_nombre_negocio.text = config['nombre_negocio'] or ''
                self.ids.input_nit.text           = config['nit_rut']       or ''
                self.ids.input_telefono.text      = config['telefono']      or ''
                self.ids.input_direccion.text     = config['direccion']     or ''
                self.ids.input_margen.text        = str(config['margen_ganancia'] or 35.0)
                self.ids.input_stock_minimo.text  = str(config['stock_minimo']   or 5)
                
                app = MDApp.get_running_app()
                self.ids.switch_tema.active = (app.theme_cls.theme_style == "Dark")
            except Exception as e:
                print(f'[Config] Error cargando campos: {e}')

    def guardar_configuracion(self):
        print(f"[Config] Intentando guardar...")
        print(f"[Config] margen_text='{self.ids.input_margen.text}'  stock_text='{self.ids.input_stock_minimo.text}'")
        try:
            margen = float(self.ids.input_margen.text)
            stock_min = int(self.ids.input_stock_minimo.text)
        except ValueError as e:
            print(f"[Config] ValueError: {e}")
            self.mostrar_alerta("Valores numéricos inválidos.", tipo="error")
            return
        
        datos = {
            'nombre_negocio': self.ids.input_nombre_negocio.text,
            'nit_rut': self.ids.input_nit.text,
            'telefono': self.ids.input_telefono.text,
            'direccion': self.ids.input_direccion.text,
            'margen_ganancia': margen,
            'stock_minimo': stock_min
        }
        print(f"[Config] Datos a guardar: {datos}")
        guardar_config(datos)
        
        # Verificar que se guardó correctamente
        from database import obtener_config
        verificacion = obtener_config()
        print(f"[Config] DB tras guardar: margen={verificacion['margen_ganancia']}  stock={verificacion['stock_minimo']}")
        
        # Actualizar los campos de texto con los nuevos valores guardados
        self.ids.input_margen.text = str(margen)
        self.ids.input_stock_minimo.text = str(stock_min)
        # También actualizar nombre del negocio si cambió
        self.ids.input_nombre_negocio.text = datos['nombre_negocio']
        self.ids.input_nit.text = datos['nit_rut']
        self.ids.input_telefono.text = datos['telefono']
        self.ids.input_direccion.text = datos['direccion']

        # Actualizar propiedades de la app (título y stock mínimo) para que los widgets que dependen de ellas se refresquen
        app = MDApp.get_running_app()
        app.stock_minimo = stock_min
        if datos['nombre_negocio']:
            app.title = datos['nombre_negocio']
        
        # Refrescar reportes para que el nuevo margen se refleje de inmediato
        try:
            app = MDApp.get_running_app()
            from kivy.clock import Clock
            pantalla_inv = app.root.get_screen('inventario')
            Clock.schedule_once(lambda dt: pantalla_inv.recargar_todo())
        except Exception as ex:
            print(f"[Config] Error en cargar_reportes: {ex}")
            

        self.mostrar_alerta("Configuración guardada", tipo="success")

    def crear_respaldo(self):
        import shutil
        import os
        from datetime import datetime
        from tkinter import Tk, filedialog
        
        from database import DB_PATH
        db_path = DB_PATH
        backup_name = f"ventatienda_datos_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        
        root = Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        ruta = filedialog.asksaveasfilename(
            title="Guardar Respaldo de Seguridad", 
            defaultextension=".db", 
            filetypes=[("Database Files", "*.db")], 
            initialfile=backup_name
        )
        root.destroy()
        
        if not ruta:
            return
            
        try:
            shutil.copy(db_path, ruta)
            self.mostrar_alerta(f"Respaldo guardado con éxito.", tipo="success")
        except Exception as e:
            self.mostrar_alerta(f"Error al crear respaldo: {e}", tipo="error")

    def cambiar_tema(self, instance, value):
        app = MDApp.get_running_app()
        if value:
            app.theme_cls.theme_style = "Dark"
        else:
            app.theme_cls.theme_style = "Light"
        app._actualizar_colores_tema()

    def mostrar_alerta(self, mensaje, tipo="success"):
        color = VERDE_PRINCIPAL if tipo == "success" else ROJO
        MDSnackbar(
            MDLabel(
                text=mensaje,
                theme_text_color="Custom",
                text_color=(1, 1, 1, 1)
            ),
            md_bg_color=color,
            pos_hint={"center_x": 0.5, "top": 0.95},
            size_hint_x=0.8,
            y="24dp"
        ).open()


class VentaTiendaApp(MDApp):
    stock_minimo = NumericProperty(5)

    # Propiedades de color dinámicas para modo oscuro/claro
    color_fondo         = ColorProperty([0.97, 0.98, 0.97, 1])
    color_card          = ColorProperty([1, 1, 1, 1])
    color_card_tonal    = ColorProperty([0.13, 0.18, 0.13, 1])  # oscuro suave verde
    color_verde_suave   = ColorProperty([0.9, 0.97, 0.92, 1])
    color_morado_suave  = ColorProperty([0.95, 0.93, 0.98, 1])
    color_azul_suave    = ColorProperty([0.92, 0.95, 0.98, 1])
    color_naranja_suave = ColorProperty([0.98, 0.94, 0.90, 1])
    color_nav_panel     = ColorProperty([1, 1, 1, 1])
    color_nav_text_norm = ColorProperty([0.5, 0.5, 0.5, 1])

    def _actualizar_colores_tema(self):
        dark = self.theme_cls.theme_style == "Dark"
        if dark:
            self.color_fondo         = [0.08, 0.09, 0.10, 1]
            self.color_card          = [0.13, 0.16, 0.18, 1]
            self.color_verde_suave   = [0.06, 0.20, 0.10, 1]
            self.color_morado_suave  = [0.18, 0.10, 0.26, 1]
            self.color_azul_suave    = [0.08, 0.17, 0.28, 1]
            self.color_naranja_suave = [0.28, 0.16, 0.06, 1]
            self.color_nav_panel     = [0.10, 0.12, 0.14, 1]
            self.color_nav_text_norm = [0.55, 0.60, 0.65, 1]
        else:
            self.color_fondo         = [0.97, 0.98, 0.97, 1]
            self.color_card          = [1, 1, 1, 1]
            self.color_verde_suave   = [0.9, 0.97, 0.92, 1]
            self.color_morado_suave  = [0.95, 0.93, 0.98, 1]
            self.color_azul_suave    = [0.92, 0.95, 0.98, 1]
            self.color_naranja_suave = [0.98, 0.94, 0.90, 1]
            self.color_nav_panel     = [1, 1, 1, 1]
            self.color_nav_text_norm = [0.5, 0.5, 0.5, 1]

    def verificar_cierre(self, *args):
        if self.ventas_exportadas:
            return False

        def ir_a_reportes(*args):
            self.dialogo_cierre.dismiss()
            if self.root:
                pantalla = self.root.get_screen('inventario')
                if 'bottom_nav' in pantalla.ids:
                    pantalla.ids.bottom_nav.switch_tab('tab_reportes')

        self.dialogo_cierre = MDDialog(
            title="[color=ee2222]¡Atención![/color]",
            text="No has realizado la exportación de las ventas del día en VentaTienda. ¿Estás seguro de que deseas salir sin guardar tu reporte?",
            buttons=[
                MDFlatButton(text="Exportar Ahora", theme_text_color="Custom", text_color=[0.08, 0.53, 0.25, 1], on_release=ir_a_reportes),
                MDRaisedButton(text="Salir de todas formas", md_bg_color=[0.85, 0.25, 0.25, 1], on_release=lambda x: self.stop())
            ]
        )
        self.dialogo_cierre.open()
        return True

    def build(self):
        self.ventas_exportadas = False
        Window.bind(on_request_close=self.verificar_cierre)

        # Cargar el archivo .kv explícitamente (compatible con PyInstaller)
        Builder.load_file(resource_path('ventatienda.kv'))

        iniciar_db()
        config = obtener_config()
        if config:
            self.stock_minimo = config['stock_minimo']
            self.title = config['nombre_negocio'] or "Mi Negocio"
        else:
            self.title = "Mi Negocio"
            
        self.theme_cls.primary_palette = "Green"
        self.theme_cls.theme_style = "Light"
        self._actualizar_colores_tema()
        
        sm = MDScreenManager()
        sm.add_widget(PantallaInventario(name='inventario'))
        sm.add_widget(PantallaConfiguracion(name='configuracion'))
        return sm


if __name__ == "__main__":
    VentaTiendaApp().run()
