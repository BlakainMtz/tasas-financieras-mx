// ===============================
// API: Guardar tasas financieras
// ===============================
add_action('rest_api_init', function () {
	register_rest_route('tasas/v1', '/update', array(
		'methods'  => 'POST',
		'callback' => 'guardar_tasas_json',
		'permission_callback' => '__return_true'
	));
	register_rest_route('tasas/v1', '/test', array(
		'methods'  => 'GET',
		'callback' => function () {
			return ['ok' => true];
		},
		'permission_callback' => '__return_true'
	));
});
function guardar_tasas_json($request) {
	$raw = $request->get_body();
	error_log('RAW BODY: ' . $raw);
	$data = json_decode($raw, true);
	error_log('JSON DECODED: ' . print_r($data, true));
	if (!$data || !is_array($data)) {
		error_log('JSON INVALIDO');
		return new WP_REST_Response([
			'status' => 'error',
			'message' => 'JSON inválido o vacío'
		], 400);
	}
	update_option('tasas_json', $data);
	error_log('DATOS GUARDADOS');
	return new WP_REST_Response([
		'status' => 'ok',
		'message' => 'Datos guardados correctamente'
	], 200);
}
// ===============================
// SHORTCODE FINAL
// ===============================
function mostrar_tasas_tabla() {
	$data = get_option('tasas_json');
	if (!$data || !is_array($data)) {
		return '<p>No hay datos disponibles.</p>';
	}
 
	// Tasas por institución: [a_la_vista, 1_mes, 3_meses, 6_meses, 1_ano]
	$filas = [
		'CETES'       => [null, $data['CETES']['1_mes'] ?? null, $data['CETES']['3_meses'] ?? null, $data['CETES']['6_meses'] ?? null, $data['CETES']['1_ano'] ?? null],
		'BONDDIA'     => [$data['BONDDIA']['a_la_vista'] ?? null, null, null, null, null],
		'NU'          => [$data['NU']['cajita_turbo'] ?? null, $data['NU']['1_mes'] ?? null, $data['NU']['3_meses'] ?? null, $data['NU']['6_meses'] ?? null, null],
		'REVOLUT'     => [$data['REVOLUT']['a_la_vista'] ?? null, null, null, null, null],
		'SUPERTASAS'  => [$data['SUPERTASAS']['a_la_vista'] ?? null, $data['SUPERTASAS']['1_mes'] ?? null, $data['SUPERTASAS']['3_meses'] ?? null, $data['SUPERTASAS']['6_meses'] ?? null, $data['SUPERTASAS']['1_ano'] ?? null],
		'MIFEL'       => [$data['MIFEL']['a_la_vista'] ?? null, null, null, null, null],
		'FINSUS'      => [$data['FINSUS']['a_la_vista'] ?? null, $data['FINSUS']['1_mes'] ?? null, $data['FINSUS']['3_meses'] ?? null, $data['FINSUS']['6_meses'] ?? null, $data['FINSUS']['1_ano'] ?? null],
		'DIDICUENTA'  => [$data['DIDICUENTA']['a_la_vista'] ?? null, null, null, null, null],
		'KLAR'        => [$data['KLAR']['tasa_max'] ?? null, $data['KLAR']['1_mes'] ?? null, $data['KLAR']['3_meses'] ?? null, $data['KLAR']['6_meses'] ?? null, $data['KLAR']['1_ano'] ?? null],
		'PLATA'       => [$data['PLATA']['tasa_max'] ?? null, $data['PLATA']['1_mes'] ?? null, $data['PLATA']['3_meses'] ?? null, $data['PLATA']['6_meses'] ?? null, $data['PLATA']['1_ano'] ?? null],
		'OPENBANK'    => [$data['OPENBANK']['a_la_vista'] ?? null, null, null, null, null],
		'MERCADOPAGO' => [$data['MERCADOPAGO']['a_la_vista'] ?? null, null, null, null, null],
	];
 
	// Mejor tasa por columna
	$mejor = [0, 0, 0, 0, 0];
	for ($c = 0; $c < 5; $c++) {
		$vals = [];
		foreach ($filas as $row) {
			if (is_numeric($row[$c])) $vals[] = floatval($row[$c]);
		}
		$mejor[$c] = !empty($vals) ? max($vals) : 0;
	}
 
	// Helper: renderizar celda con highlight si es la mejor de su columna (closure para evitar redeclaración)
	$render_tasa = function($valor, $mejor_col) {
		if (!is_numeric($valor) || $valor === null) return '<span style="color:#ccc;">—</span>';
		$texto = rtrim(rtrim(number_format(floatval($valor), 2, '.', ''), '0'), '.') . '%';
		if (floatval($valor) == floatval($mejor_col)) {
			return '<span class="tasas-mejor">' . $texto . '</span>';
		}
		return $texto;
	};
 
	// Metadatos por institución: tipo, badge class, fuente URL, crear cuenta URL, rel attrs
	$meta = [
		'CETES'       => ['Gobierno', 'tasas-tipo-gobierno', 'https://www.cetesdirecto.com/sites/portal/inicio', 'https://www.cetesdirecto.com/sites/portal/inicio', 'noopener'],
		'BONDDIA'     => ['Gobierno', 'tasas-tipo-gobierno', 'https://www.cetesdirecto.com/tablas/valores_gubernamentales/bonddia.html', 'https://www.cetesdirecto.com/sites/portal/inicio', 'noopener'],
		'NU'          => ['Banco', 'tasas-tipo-banco', 'https://nu.com.mx/cuenta/rendimientos/', 'https://nu.com.mx/mgm/?id=tIdI1ax-yJmgs6-eIt94GA&msg=06478&utm_channel=referral&utm_medium=other&utm_source=mgm', 'noopener nofollow sponsored'],
		'DIDICUENTA'  => ['SOFIPO', 'tasas-tipo-sofipo', 'https://web.didiglobal.com/mx/jpsofiexpress/didi-cuenta/', 'https://web.didiglobal.com/mx/jpsofiexpress/didi-cuenta/', 'noopener'],
		'OPENBANK'    => ['Banco', 'tasas-tipo-banco', 'https://www.openbank.mx/', 'https://www.openbank.mx/', 'noopener'],
		'MERCADOPAGO' => ['Fintech', 'tasas-tipo-fintech', 'https://www.mercadopago.com.mx/cuenta', 'https://www.mercadopago.com.mx/cuenta', 'noopener'],
		'REVOLUT'     => ['Banco', 'tasas-tipo-banco', 'https://www.revolut.com/es-MX/instant-access-savings/', 'https://revolut.com/referral/?referral-code=ricardomtzabarca!JUN1-26-AR-MX-H1&geo-redirect', 'noopener nofollow sponsored'],
		'MIFEL'       => ['Banco', 'tasas-tipo-banco', 'https://www.mifel.com.mx/personas/cuentas/cuenta-digital', 'https://www.mifel.com.mx/personas/cuentas/cuenta-digital', 'noopener'],
		'SUPERTASAS'  => ['SOFIPO', 'tasas-tipo-sofipo', 'https://crediclub.com/', 'https://crediclub.com/', 'noopener'], // Supertasas migró a Crediclub (sep-2026). La ruta /inversión rebota al home en carga directa (SPA Framer), por eso se enlaza al home.
		'FINSUS'      => ['SOFIPO', 'tasas-tipo-sofipo', 'https://finsus.mx/personas/inversiones', 'https://finsus.onelink.me/MWGf/k3keny16?deep_link_sub1=MARTINEZR13792757', 'noopener nofollow sponsored'],
		'KLAR'        => ['SOFIPO', 'tasas-tipo-sofipo', 'https://www.klar.mx/gat', 'https://www.klar.mx/', 'noopener'],
		'PLATA'       => ['Banco', 'tasas-tipo-banco', 'https://bancoplata.mx/es/cuenta', 'https://bancoplata.mx/es/card/cuenta', 'noopener'],
	];
 
	// Nombres para mostrar
	$nombres = [
		'CETES' => 'CETES', 'BONDDIA' => 'BONDDIA', 'NU' => 'NU',
		'DIDICUENTA' => 'DIDICUENTA', 'OPENBANK' => 'OPENBANK',
		'MERCADOPAGO' => 'MERCADO PAGO', 'REVOLUT' => 'REVOLUT',
		'MIFEL' => 'MIFEL', 'SUPERTASAS' => 'CREDICLUB',
		'FINSUS' => 'FINSUS', 'KLAR' => 'KLAR', 'PLATA' => 'BANCO PLATA',
	];
 
	ob_start();
	?>
	<style>
		.tasas-table { width:100%; min-width:850px; border-collapse:separate; border-spacing:0; border-radius:12px; overflow:hidden; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size:14px; table-layout:fixed; }
		.tasas-table thead tr { background:#00166c; }
		.tasas-table thead th { padding:14px 12px; color:#fff; font-weight:600; font-size:13px; text-transform:uppercase; letter-spacing:0.5px; text-align:center; }
		.tasas-table thead th:first-child { text-align:left; }
		.tasas-table tbody tr { transition: background 0.15s; }
		.tasas-table tbody tr:hover { background:#f0f4ff; }
		.tasas-table tbody tr:nth-child(even) { background:#f9fafb; }
		.tasas-table tbody tr:nth-child(even):hover { background:#f0f4ff; }
		.tasas-table tbody td { padding:14px 12px; text-align:center; border-bottom:1px solid #f0f0f0; color:#333; }
		.tasas-table tbody td:first-child { text-align:left; font-weight:700; color:#1a1a1a; }
		.tasas-tipo { display:inline-block; padding:3px 10px; border-radius:20px; font-size:11px; font-weight:600; }
		.tasas-tipo-gobierno { background:#e0edff; color:#00166c; }
		.tasas-tipo-sofipo { background:#e8f5e9; color:#1b5e20; }
		.tasas-tipo-banco { background:#fff3e0; color:#e65100; }
		.tasas-tipo-fintech { background:#f3e5f5; color:#7b1fa2; }
		.tasas-mejor { background:#1D9E75; color:#fff; font-weight:700; padding:4px 10px; border-radius:6px; display:inline-block; }
		.tasas-btn-fuente { color:#185FA5; text-decoration:none; font-weight:500; font-size:13px; }
		.tasas-btn-fuente:hover { text-decoration:underline; }
		.tasas-btn-crear { display:inline-block; padding:6px 14px; background:#00166c; color:#fff; border-radius:6px; font-size:12px; font-weight:600; text-decoration:none; transition: background 0.2s, transform 0.15s; }
		.tasas-btn-crear:hover { background:#1D9E75; transform:translateY(-1px); }
		.tasas-footer { text-align:center; font-size:12px; margin-top:12px; color:#999; }
	</style>
	<div id="tabla-tasas" style="width:100%; margin:auto; overflow-x:auto;">
	  <table class="tasas-table">
		<thead>
		  <tr>
			<th style="text-align:left;">Institución</th>
			<th>Tipo</th>
			<th>A la vista</th>
			<th>1 mes</th>
			<th>3 meses</th>
			<th>6 meses</th>
			<th>1 año</th>
			<th>Fuente</th>
			<th>Abrir cuenta</th>
		  </tr>
		</thead>
		<tbody>
		<?php foreach ($filas as $key => $tasas): ?>
		<tr>
			<td><?php echo $nombres[$key]; ?></td>
			<td><span class="tasas-tipo <?php echo $meta[$key][1]; ?>"><?php echo $meta[$key][0]; ?></span></td>
			<?php for ($c = 0; $c < 5; $c++): ?>
			<td><?php echo $render_tasa($tasas[$c], $mejor[$c]); ?></td>
			<?php endfor; ?>
			<td><a class="tasas-btn-fuente" href="<?php echo esc_url($meta[$key][2]); ?>" target="_blank">Ver sitio</a></td>
			<td><a class="tasas-btn-crear" href="<?php echo esc_url($meta[$key][3]); ?>" target="_blank" rel="<?php echo esc_attr($meta[$key][4]); ?>">Crear cuenta</a></td>
		</tr>
		<?php endforeach; ?>
		</tbody>
	  </table>
	  <p class="tasas-footer">
		Última actualización: <?php
if (!empty($data['last_update'])) {
	$fecha = date_create($data['last_update']);
	echo date_format($fecha, 'd/m/Y H:i');
} else {
	echo '—';
}
?>
	  </p>
	</div>
	<?php
	return ob_get_clean();
}
add_shortcode('tasas_financieras', 'mostrar_tasas_tabla');
 
