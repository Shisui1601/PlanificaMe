"""
mail_service.py — Servicio de correos de PlanificaMe
Maneja todos los tipos de notificaciones por email con plantillas HTML.
Usa la API HTTP de Brevo (evita bloqueos de puerto SMTP en Render free tier).
"""
import requests
from ..config import settings
import logging

logger = logging.getLogger(__name__)


# ════════════════════════════════════════
# PLANTILLA BASE HTML
# ════════════════════════════════════════

def _base_template(content: str, color: str = "#7c5aff") -> str:
    """Plantilla HTML base para todos los correos"""
    return f"""
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>PlanificaMe</title>
</head>
<body style="margin:0;padding:0;background:#f0f2f8;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f2f8;padding:40px 20px;">
    <tr>
      <td align="center">
        <table width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;">

          <!-- HEADER -->
          <tr>
            <td style="background:linear-gradient(135deg,{color},#10b981);border-radius:16px 16px 0 0;padding:28px 36px;text-align:center;">
              <h1 style="margin:0;font-size:24px;color:white;font-weight:700;letter-spacing:-0.5px;">
                📅 PlanificaMe
              </h1>
              <p style="margin:6px 0 0;font-size:13px;color:rgba(255,255,255,0.8);">
                Tu asistente de productividad
              </p>
            </td>
          </tr>

          <!-- BODY -->
          <tr>
            <td style="background:white;padding:36px;border-radius:0 0 16px 16px;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
              {content}
            </td>
          </tr>

          <!-- FOOTER -->
          <tr>
            <td style="padding:20px 36px;text-align:center;">
              <p style="margin:0;font-size:11px;color:#8888aa;">
                PlanificaMe © 2026 · Este correo fue enviado automáticamente, no respondas a este mensaje.
              </p>
              <p style="margin:8px 0 0;">
                <a href="{settings.FRONTEND_URL}" style="font-size:12px;color:{color};text-decoration:none;font-weight:600;">
                  Ir a PlanificaMe →
                </a>
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""


def _info_row(icon: str, label: str, value: str) -> str:
    return f"""
    <tr>
      <td style="padding:8px 0;border-bottom:1px solid #f0f2f8;">
        <span style="font-size:15px;margin-right:10px;">{icon}</span>
        <span style="font-size:12px;color:#8888aa;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">{label}</span>
        <span style="display:block;margin-left:28px;font-size:14px;color:#111128;font-weight:500;margin-top:2px;">{value}</span>
      </td>
    </tr>"""


# ════════════════════════════════════════
# CLASE PRINCIPAL
# ════════════════════════════════════════

class MailService:
    """Servicio central de envío de correos"""

    @staticmethod
    def send_email(to_email: str, subject: str, html_content: str, text_content: str = None) -> bool:
        """Envía un correo via Brevo HTTP API. Devuelve True si fue exitoso."""
        api_key = getattr(settings, 'BREVO_API_KEY', None)
        if not api_key:
            logger.warning("BREVO_API_KEY no configurado — correo no enviado")
            return False
        try:
            payload = {
                "sender": {
                    "name": settings.SENDER_NAME,
                    "email": settings.SENDER_EMAIL
                },
                "to": [{"email": to_email}],
                "subject": subject,
                "htmlContent": html_content,
            }
            if text_content:
                payload["textContent"] = text_content

            response = requests.post(
                "https://api.brevo.com/v3/smtp/email",
                headers={
                    "api-key": api_key,
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=15
            )
            if response.status_code in (200, 201):
                logger.info(f"✉️  Correo enviado → {to_email} | {subject}")
                return True
            else:
                logger.error(f"❌ Brevo API error {response.status_code}: {response.text}")
                return False

        except Exception as e:
            logger.error(f"❌ Error enviando correo a {to_email}: {str(e)}")
            return False

    # ─────────────────────────────────────
    # 1. RECORDATORIO DE ACTIVIDAD
    # ─────────────────────────────────────
    @staticmethod
    def send_reminder_email(event_title: str, to_email: str, event_date: str,
                             event_time: str, reminder_minutes: int) -> bool:
        subject = f"🔔 Recordatorio: {event_title}"
        time_label = f"{reminder_minutes} min" if reminder_minutes < 60 else (
            "1 hora" if reminder_minutes == 60 else "1 día")

        content = f"""
        <h2 style="margin:0 0 6px;font-size:22px;color:#111128;">🔔 Recordatorio de actividad</h2>
        <p style="margin:0 0 24px;font-size:14px;color:#44446a;">
          Tu actividad comienza en <strong>{time_label}</strong>.
        </p>
        <div style="background:#f7f8ff;border-radius:12px;padding:20px;margin-bottom:24px;">
          <h3 style="margin:0 0 16px;font-size:16px;color:#7c5aff;">{event_title}</h3>
          <table width="100%" cellpadding="0" cellspacing="0">
            {_info_row("📅", "Fecha", event_date)}
            {_info_row("🕐", "Hora", event_time)}
            {_info_row("⏰", "Recordatorio", f"{time_label} antes")}
          </table>
        </div>
        <div style="text-align:center;">
          <a href="{settings.FRONTEND_URL}" style="display:inline-block;background:linear-gradient(135deg,#7c5aff,#5b3acc);color:white;text-decoration:none;padding:12px 28px;border-radius:8px;font-weight:600;font-size:14px;">
            Ver actividad →
          </a>
        </div>"""

        return MailService.send_email(
            to_email, subject,
            _base_template(content, "#7c5aff"),
            f"Recordatorio: {event_title} comienza en {time_label}."
        )

    # ─────────────────────────────────────
    # 2. ADVERTENCIA DE FECHA LÍMITE
    # ─────────────────────────────────────
    @staticmethod
    def send_deadline_warning_email(event_title: str, to_email: str,
                                     days_left: int, deadline_date: str) -> bool:
        if days_left < 0:
            subject = f"🚨 Venció: {event_title}"
            badge = f"<span style='background:#fee2e2;color:#dc2626;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:700;'>Venció hace {abs(days_left)} día(s)</span>"
            color = "#dc2626"
            message = f"Esta actividad venció hace <strong>{abs(days_left)} día(s)</strong>. Actualiza su estado."
        elif days_left == 0:
            subject = f"⚠️ ¡Vence hoy!: {event_title}"
            badge = "<span style='background:#fef3c7;color:#d97706;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:700;'>¡Vence hoy!</span>"
            color = "#d97706"
            message = "Esta actividad <strong>vence hoy</strong>. ¡No la olvides!"
        elif days_left <= 3:
            subject = f"⏳ Vence pronto: {event_title}"
            badge = f"<span style='background:#fef3c7;color:#d97706;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:700;'>Faltan {days_left} día(s)</span>"
            color = "#d97706"
            message = f"Solo faltan <strong>{days_left} día(s)</strong> para que venza esta actividad."
        else:
            subject = f"📅 Recordatorio de deadline: {event_title}"
            badge = f"<span style='background:#d1fae5;color:#059669;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:700;'>Faltan {days_left} día(s)</span>"
            color = "#059669"
            message = f"Faltan <strong>{days_left} días</strong> para la fecha límite."

        content = f"""
        <h2 style="margin:0 0 6px;font-size:22px;color:#111128;">⏳ Fecha límite</h2>
        <p style="margin:0 0 20px;">{badge}</p>
        <div style="background:#f7f8ff;border-radius:12px;padding:20px;margin-bottom:20px;">
          <h3 style="margin:0 0 16px;font-size:16px;color:{color};">{event_title}</h3>
          <table width="100%" cellpadding="0" cellspacing="0">
            {_info_row("📅", "Fecha límite", deadline_date)}
          </table>
        </div>
        <p style="font-size:14px;color:#44446a;margin-bottom:24px;">{message}</p>
        <div style="text-align:center;">
          <a href="{settings.FRONTEND_URL}" style="display:inline-block;background:linear-gradient(135deg,{color},{color}cc);color:white;text-decoration:none;padding:12px 28px;border-radius:8px;font-weight:600;font-size:14px;">
            Actualizar estado →
          </a>
        </div>"""

        return MailService.send_email(
            to_email, subject,
            _base_template(content, color),
            f"{subject} — Fecha límite: {deadline_date}"
        )

    # ─────────────────────────────────────
    # 3. INVITACIÓN A CALENDARIO
    # ─────────────────────────────────────
    @staticmethod
    def send_calendar_invite_email(to_email: str, to_name: str, inviter_name: str,
                                    calendar_name: str, calendar_color: str,
                                    role: str) -> bool:
        subject = f"📅 {inviter_name} te invitó al calendario \"{calendar_name}\""
        role_label = "Editor (puede crear y editar)" if role == "editor" else "Miembro (solo lectura)"

        content = f"""
        <h2 style="margin:0 0 6px;font-size:22px;color:#111128;">¡Tienes una invitación!</h2>
        <p style="margin:0 0 24px;font-size:14px;color:#44446a;">
          <strong>{inviter_name}</strong> te ha invitado a colaborar en un calendario de PlanificaMe.
        </p>
        <div style="background:#f7f8ff;border-radius:12px;padding:20px;margin-bottom:24px;border-left:4px solid {calendar_color};">
          <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;">
            <div style="width:36px;height:36px;border-radius:10px;background:{calendar_color};display:inline-block;"></div>
            <h3 style="margin:0;font-size:18px;color:#111128;display:inline-block;margin-left:8px;">{calendar_name}</h3>
          </div>
          <table width="100%" cellpadding="0" cellspacing="0">
            {_info_row("👤", "Invitado por", inviter_name)}
            {_info_row("🎭", "Tu rol", role_label)}
          </table>
        </div>
        <p style="font-size:13px;color:#8888aa;margin-bottom:24px;">
          Inicia sesión en PlanificaMe para ver el calendario y las actividades compartidas.
        </p>
        <div style="text-align:center;">
          <a href="{settings.FRONTEND_URL}" style="display:inline-block;background:linear-gradient(135deg,#7c5aff,#10b981);color:white;text-decoration:none;padding:12px 28px;border-radius:8px;font-weight:600;font-size:14px;">
            Abrir PlanificaMe →
          </a>
        </div>"""

        return MailService.send_email(
            to_email, subject,
            _base_template(content, calendar_color or "#7c5aff"),
            f"{inviter_name} te invitó al calendario '{calendar_name}' en PlanificaMe."
        )

    # ─────────────────────────────────────
    # 4. ACTUALIZACIÓN DE ESTADO
    # ─────────────────────────────────────
    @staticmethod
    def send_status_update_email(event_title: str, to_email: str, status: str,
                                  status_note: str = None) -> bool:
        status_map = {
            "completed":       ("✅", "Completada",             "#059669", "#d1fae5"),
            "early-voluntary": ("⚡", "Adelantada — voluntad",  "#d97706", "#fef3c7"),
            "early-forced":    ("🔀", "Adelantada — obligación","#d97706", "#fef3c7"),
            "extended":        ("📅", "Extendida",              "#3b82f6", "#dbeafe"),
            "abandoned":       ("🚫", "Abandonada",             "#dc2626", "#fee2e2"),
        }
        icon, label, color, bg = status_map.get(status, ("🕐", status, "#7c5aff", "#f0f0ff"))
        subject = f"{icon} Estado actualizado: {event_title}"

        note_block = f"""
        <div style="background:#f7f8ff;border-radius:8px;padding:14px;margin-top:16px;border-left:3px solid {color};">
          <p style="margin:0;font-size:13px;color:#44446a;"><strong>Nota:</strong> {status_note}</p>
        </div>""" if status_note else ""

        content = f"""
        <h2 style="margin:0 0 6px;font-size:22px;color:#111128;">📊 Estado actualizado</h2>
        <p style="margin:0 0 20px;font-size:14px;color:#44446a;">
          Una actividad ha cambiado de estado en PlanificaMe.
        </p>
        <div style="background:{bg};border-radius:12px;padding:20px;margin-bottom:20px;text-align:center;">
          <div style="font-size:36px;margin-bottom:8px;">{icon}</div>
          <div style="font-size:16px;font-weight:700;color:{color};">{label}</div>
          <div style="font-size:14px;color:#44446a;margin-top:8px;font-weight:600;">{event_title}</div>
        </div>
        {note_block}
        <div style="text-align:center;margin-top:24px;">
          <a href="{settings.FRONTEND_URL}" style="display:inline-block;background:linear-gradient(135deg,{color},{color}cc);color:white;text-decoration:none;padding:12px 28px;border-radius:8px;font-weight:600;font-size:14px;">
            Ver en PlanificaMe →
          </a>
        </div>"""

        return MailService.send_email(
            to_email, subject,
            _base_template(content, color),
            f"La actividad '{event_title}' fue marcada como: {label}"
        )

    # ─────────────────────────────────────
    # 5. RESUMEN SEMANAL
    # ─────────────────────────────────────
    @staticmethod
    def send_weekly_summary_email(to_email: str, user_name: str,
                                   upcoming_events: list, overdue_events: list,
                                   completed_this_week: int, week_label: str) -> bool:
        subject = f"📊 Tu resumen semanal — {week_label}"

        # Filas de eventos próximos
        upcoming_rows = ""
        if upcoming_events:
            for ev in upcoming_events[:5]:
                type_color = {"personal": "#7c5aff", "team": "#10b981", "project": "#f59e0b"}.get(ev.get("type", "personal"), "#7c5aff")
                upcoming_rows += f"""
                <tr>
                  <td style="padding:10px 0;border-bottom:1px solid #f0f2f8;">
                    <div style="display:flex;align-items:center;gap:8px;">
                      <div style="width:8px;height:8px;border-radius:50%;background:{type_color};display:inline-block;margin-right:8px;"></div>
                      <span style="font-size:13px;font-weight:600;color:#111128;">{ev.get('title','')}</span>
                    </div>
                    <div style="margin-left:16px;font-size:11px;color:#8888aa;margin-top:2px;">
                      📅 {ev.get('date','')} · 🕐 {ev.get('time','')}
                    </div>
                  </td>
                </tr>"""
        else:
            upcoming_rows = "<tr><td style='padding:12px 0;font-size:13px;color:#8888aa;'>Sin actividades próximas esta semana.</td></tr>"

        # Bloque de vencidos
        overdue_block = ""
        if overdue_events:
            overdue_list = "".join([
                f"<li style='margin-bottom:6px;font-size:13px;color:#dc2626;'>{ev.get('title','')} <span style='color:#8888aa;font-size:11px;'>(venció {ev.get('deadline_date','')})</span></li>"
                for ev in overdue_events[:5]
            ])
            overdue_block = f"""
            <div style="background:#fee2e2;border-radius:12px;padding:16px 20px;margin-top:20px;">
              <h4 style="margin:0 0 12px;font-size:14px;color:#dc2626;">🚨 Actividades vencidas ({len(overdue_events)})</h4>
              <ul style="margin:0;padding-left:16px;">{overdue_list}</ul>
            </div>"""

        content = f"""
        <h2 style="margin:0 0 4px;font-size:22px;color:#111128;">👋 Hola, {user_name}</h2>
        <p style="margin:0 0 24px;font-size:14px;color:#44446a;">Aquí tienes tu resumen de la semana en PlanificaMe.</p>

        <!-- Stats -->
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:24px;">
          <div style="background:#f0f0ff;border-radius:10px;padding:16px;text-align:center;">
            <div style="font-size:24px;font-weight:700;color:#7c5aff;">{len(upcoming_events)}</div>
            <div style="font-size:11px;color:#8888aa;margin-top:4px;">Próximas</div>
          </div>
          <div style="background:#d1fae5;border-radius:10px;padding:16px;text-align:center;">
            <div style="font-size:24px;font-weight:700;color:#059669;">{completed_this_week}</div>
            <div style="font-size:11px;color:#8888aa;margin-top:4px;">Completadas</div>
          </div>
          <div style="background:#fee2e2;border-radius:10px;padding:16px;text-align:center;">
            <div style="font-size:24px;font-weight:700;color:#dc2626;">{len(overdue_events)}</div>
            <div style="font-size:11px;color:#8888aa;margin-top:4px;">Vencidas</div>
          </div>
        </div>

        <!-- Próximas actividades -->
        <h3 style="margin:0 0 12px;font-size:15px;color:#111128;">📋 Actividades de esta semana</h3>
        <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:8px;">
          {upcoming_rows}
        </table>

        {overdue_block}

        <div style="text-align:center;margin-top:28px;">
          <a href="{settings.FRONTEND_URL}" style="display:inline-block;background:linear-gradient(135deg,#7c5aff,#10b981);color:white;text-decoration:none;padding:12px 28px;border-radius:8px;font-weight:600;font-size:14px;">
            Ver mi calendario →
          </a>
        </div>"""

        return MailService.send_email(
            to_email, subject,
            _base_template(content, "#7c5aff"),
            f"Resumen semanal de PlanificaMe para {user_name}"
        )

    # ─────────────────────────────────────
    # ─────────────────────────────────────
    # 7. NUEVA ACTIVIDAD en calendario compartido
    # ─────────────────────────────────────
    @staticmethod
    def send_event_created_email(
        to_email: str, event_title: str, event_type: str, event_date: str,
        event_time: str, creator_name: str, calendar_name: str,
        calendar_color: str = "#7c5aff", description: str = None,
        deadline_date: str = None, duration_minutes: int = None
    ) -> bool:
        type_map = {
            "personal": ("🔒", "Personal", "#7c5aff"),
            "team":     ("👥", "Equipo",   "#10b981"),
            "project":  ("🎯", "Meta",     "#f59e0b"),
        }
        type_icon, type_label, type_color = type_map.get(event_type, ("📋", event_type, "#7c5aff"))
        subject = f"{type_icon} Nueva actividad: {event_title}"
        dur_str = f"{duration_minutes} min" if duration_minutes else ""
        desc_block = (
            f'''<div style="background:#f7f8ff;border-radius:8px;padding:12px 14px;margin-top:12px;border-left:3px solid #7c5aff;">
              <p style="margin:0;font-size:13px;color:#44446a;">{description}</p></div>'''
        ) if description else ""
        deadline_row = _info_row("⏳", "Fecha límite", deadline_date) if deadline_date else ""
        dur_row = _info_row("⏱️", "Duración", dur_str) if dur_str else ""
        body = f'''
        <h2 style="margin:0 0 6px;font-size:22px;color:#111128;">✨ Nueva actividad creada</h2>
        <p style="margin:0 0 20px;font-size:14px;color:#44446a;">
          <strong>{creator_name}</strong> creó una actividad en <strong style="color:{calendar_color}">{calendar_name}</strong>.
        </p>
        <div style="background:#f7f8ff;border-radius:12px;padding:20px;margin-bottom:20px;border-top:4px solid {type_color};">
          <div style="margin-bottom:12px;">
            <span style="background:{type_color}22;color:{type_color};padding:3px 10px;border-radius:20px;font-size:12px;font-weight:700;">{type_icon} {type_label}</span>
          </div>
          <h3 style="margin:0 0 16px;font-size:18px;color:#111128;">{event_title}</h3>
          <table width="100%" cellpadding="0" cellspacing="0">
            {_info_row("👤", "Creado por", creator_name)}
            {_info_row("📅", "Fecha", event_date)}
            {_info_row("🕐", "Hora", event_time)}
            {dur_row}
            {deadline_row}
          </table>
          {desc_block}
        </div>
        <div style="text-align:center;">
          <a href="{settings.FRONTEND_URL}" style="display:inline-block;background:linear-gradient(135deg,{type_color},{type_color}cc);color:white;text-decoration:none;padding:12px 28px;border-radius:8px;font-weight:600;font-size:14px;">Ver en PlanificaMe &rarr;</a>
        </div>'''
        return MailService.send_email(to_email, subject, _base_template(body, type_color),
            f"{creator_name} creó \'{event_title}\' en {calendar_name}")

    # ─────────────────────────────────────
    # 8. ACTIVIDAD EDITADA en calendario compartido
    # ─────────────────────────────────────
    @staticmethod
    def send_event_updated_email(
        to_email: str, event_title: str, editor_name: str,
        calendar_name: str, calendar_color: str = "#7c5aff", changes: list = None
    ) -> bool:
        subject = f"✏️ Actividad editada: {event_title}"
        changes_rows = ""
        if changes:
            for ch in changes:
                field = ch.get("field", "")
                old_v = ch.get("old", "—")
                new_v = ch.get("new", "")
                changes_rows += (
                    f'''<tr><td style="padding:6px 0;border-bottom:1px solid #f0f2f8;font-size:13px;color:#44446a;">
                      <strong style="color:#111128;">{field}</strong>:
                      <span style="color:#8888aa;text-decoration:line-through;margin:0 6px;">{old_v}</span>
                      <span style="color:#059669;">&rarr; {new_v}</span></td></tr>'''
                )
        else:
            changes_rows = '<tr><td style="padding:8px 0;font-size:13px;color:#44446a;">La actividad fue modificada.</td></tr>'
        body = f'''
        <h2 style="margin:0 0 6px;font-size:22px;color:#111128;">✏️ Actividad actualizada</h2>
        <p style="margin:0 0 20px;font-size:14px;color:#44446a;">
          <strong>{editor_name}</strong> editó una actividad en <strong style="color:{calendar_color}">{calendar_name}</strong>.
        </p>
        <div style="background:#f7f8ff;border-radius:12px;padding:20px;margin-bottom:20px;border-left:4px solid #3b82f6;">
          <h3 style="margin:0 0 16px;font-size:16px;color:#111128;">📋 {event_title}</h3>
          <p style="margin:0 0 12px;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;color:#8888aa;">Cambios realizados</p>
          <table width="100%" cellpadding="0" cellspacing="0">{changes_rows}</table>
        </div>
        <div style="text-align:center;">
          <a href="{settings.FRONTEND_URL}" style="display:inline-block;background:linear-gradient(135deg,#3b82f6,#1d4ed8);color:white;text-decoration:none;padding:12px 28px;border-radius:8px;font-weight:600;font-size:14px;">Ver actividad &rarr;</a>
        </div>'''
        return MailService.send_email(to_email, subject, _base_template(body, "#3b82f6"),
            f"{editor_name} editó \'{event_title}\' en {calendar_name}")

    # ─────────────────────────────────────
    # 9. CAMBIO DE ESTADO — a miembros del calendario
    # ─────────────────────────────────────
    @staticmethod
    def send_status_team_email(
        to_email: str, event_title: str, new_status: str, changed_by: str,
        calendar_name: str, calendar_color: str = "#7c5aff", status_note: str = None
    ) -> bool:
        status_map = {
            "completed":       ("✅", "Completada",             "#059669", "#d1fae5"),
            "early-voluntary": ("⚡", "Adelantada — voluntad",  "#d97706", "#fef3c7"),
            "early-forced":    ("🔀", "Adelantada — obligación","#d97706", "#fef3c7"),
            "extended":        ("📅", "Extendida",              "#3b82f6", "#dbeafe"),
            "abandoned":       ("🚫", "Abandonada",             "#dc2626", "#fee2e2"),
        }
        icon, label, color, bg = status_map.get(new_status, ("🕐", new_status, "#7c5aff", "#f0f0ff"))
        subject = f"{icon} Estado actualizado: {event_title}"
        note_block = (
            f'''<div style="background:#f7f8ff;border-radius:8px;padding:12px 14px;margin-top:12px;border-left:3px solid {color};">
              <p style="margin:0;font-size:13px;color:#44446a;"><strong>Nota:</strong> {status_note}</p></div>'''
        ) if status_note else ""
        body = f'''
        <h2 style="margin:0 0 6px;font-size:22px;color:#111128;">📊 Actualización de estado</h2>
        <p style="margin:0 0 20px;font-size:14px;color:#44446a;">
          <strong>{changed_by}</strong> actualizó el estado de una actividad en <strong style="color:{calendar_color}">{calendar_name}</strong>.
        </p>
        <div style="background:{bg};border-radius:12px;padding:24px;margin-bottom:20px;text-align:center;">
          <div style="font-size:42px;margin-bottom:10px;">{icon}</div>
          <div style="font-size:18px;font-weight:700;color:{color};margin-bottom:8px;">{label}</div>
          <div style="font-size:15px;color:#111128;font-weight:600;">{event_title}</div>
          <div style="font-size:12px;color:#8888aa;margin-top:6px;">Actualizado por {changed_by}</div>
        </div>
        {note_block}
        <div style="text-align:center;margin-top:24px;">
          <a href="{settings.FRONTEND_URL}" style="display:inline-block;background:linear-gradient(135deg,{color},{color}cc);color:white;text-decoration:none;padding:12px 28px;border-radius:8px;font-weight:600;font-size:14px;">Ver en PlanificaMe &rarr;</a>
        </div>'''
        return MailService.send_email(to_email, subject, _base_template(body, color),
            f"{changed_by} marcó \'{event_title}\' como {label} en {calendar_name}")


    # 6. BIENVENIDA al registrarse
    # ─────────────────────────────────────
    @staticmethod
    def send_welcome_email(to_email: str, user_name: str) -> bool:
        subject = f"¡Bienvenido a PlanificaMe, {user_name}! 🎉"

        content = f"""
        <div style="text-align:center;margin-bottom:28px;">
          <div style="font-size:56px;margin-bottom:12px;">🎉</div>
          <h2 style="margin:0 0 8px;font-size:24px;color:#111128;">¡Bienvenido, {user_name}!</h2>
          <p style="margin:0;font-size:15px;color:#44446a;">Tu cuenta en PlanificaMe ha sido creada exitosamente.</p>
        </div>
        <div style="background:#f7f8ff;border-radius:12px;padding:20px;margin-bottom:24px;">
          <h3 style="margin:0 0 14px;font-size:14px;color:#7c5aff;text-transform:uppercase;letter-spacing:1px;">¿Qué puedes hacer?</h3>
          <table width="100%" cellpadding="0" cellspacing="0">
            {_info_row("📅", "Calendarios", "Crea calendarios personales o de equipo")}
            {_info_row("🎯", "Proyectos Meta", "Organiza tus objetivos con fecha límite")}
            {_info_row("📋", "Actividades", "Crea tareas personales, de equipo o de proyecto")}
            {_info_row("🔔", "Recordatorios", "Recibe avisos por correo antes de cada actividad")}
          </table>
        </div>
        <div style="text-align:center;">
          <a href="{settings.FRONTEND_URL}" style="display:inline-block;background:linear-gradient(135deg,#7c5aff,#10b981);color:white;text-decoration:none;padding:14px 32px;border-radius:8px;font-weight:700;font-size:15px;">
            Comenzar ahora →
          </a>
        </div>"""

        return MailService.send_email(
            to_email, subject,
            _base_template(content, "#7c5aff"),
            f"¡Bienvenido a PlanificaMe, {user_name}! Tu cuenta ha sido creada."
        )