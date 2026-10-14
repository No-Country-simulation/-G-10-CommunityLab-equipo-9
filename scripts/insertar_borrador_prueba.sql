INSERT INTO mensajes (
    discord_id, canal_id, autor_id, autor_tipo, autor_rol, es_simulado, fecha,
    texto, contrato, version_contrato, intencion, estado_clasificacion
) VALUES (
    'disc_1234567890',
    'canal_logros_01',
    'usr_camila_01',
    'persona',
    'miembro',
    false,
    now(),
    '¡Hola a todos! Después de 6 meses en el bootcamp conseguí trabajo como Desarrolladora Fullstack 🎉',
    '{"id": "disc_1234567890", "autor": {"nombreVisible": "Camila Rodríguez", "nombreUsuario": "camila.dev"}, "canal": {"nombre": "logros"}}'::jsonb,
    'v1',
    'TESTIMONIO',
    'OK'
) ON CONFLICT (discord_id) DO NOTHING;

INSERT INTO borradores (
    mensaje_id, tipo, texto_ia, estado, consentimiento_confirmado
) VALUES (
    (SELECT id FROM mensajes WHERE discord_id = 'disc_1234567890'),
    'POST_LINKEDIN',
    '¡En CommunityLab estamos de fiesta! 🚀 Hoy celebramos a Camila Rodríguez, quien acaba de conseguir su primer empleo como Desarrolladora Fullstack tras graduarse del bootcamp. Su perseverancia y pasión por el código dieron frutos. ¡A romperla en esta nueva etapa! 🎉 #TechCareers #CommunityLab #JuniorDeveloper',
    'PENDIENTE',
    false
);
