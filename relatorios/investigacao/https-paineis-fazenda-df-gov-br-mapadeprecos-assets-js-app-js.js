
/* ================================================
PROJETO:		TEMPLATE MASHUP BÁSICO E RESPONSIVO
DESENVOLVEDOR:	JEFFERSON MATHEUS ANDRADE DA SILVA
CONTATO:		jeffersonmatheus1212@gmail.com
=================================================== */


var config = {
	host: 'qap.fazenda.df.gov.br',
	prefix: '/paineis/',
	port: 443,
	isSecure: true
};

var app ;
// Painel de estatistica
//var appID = '26a0f2da-28fd-4249-9b72-055528829f0f'; //Funcionando SRV824
var appID = 'f0176c31-3c3b-4d15-94b3-ca9f2e902854'; //Funcionando SRV815

require.config( {
	baseUrl: ( config.isSecure ? "https://" : "http://" ) + config.host + (config.port ? ":" + config.port : "") + config.prefix + "resources",
} );



require( ["js/qlik"], function ( qlik ) {
	'use strict';
	
	qlik.setOnError( function ( error ) {
		if (error) {
			$( '#popupText' ).append( error.message + "<br>" );
			$( '#popup' ).fadeIn( 1000 );

		}else{
			$( "#closePopup" ).click( function () {
				$( '#popup' ).hide();
			} );
		}
	});
	
	qlik.getGlobal(config).getAuthenticatedUser(function(reply){
		//var consultaCNPJ = window.location.search.substr(45);
        var dirData = reply.qReturn.substring(14,21);
        var userData = reply.qReturn.substring(30);
        $( "#titleApp3" ).html(dirData);
        $( "#titleApp4" ).html(userData);
   });

	function transformaData(value){
	var dataCompleta = value;
	var data = dataCompleta.substr(0,10).split('-');
	var hora = dataCompleta.substr(11,5);
	var ultimaCarga = data[2] + "/" + data[1] + "/" + data[0] + " " + hora;
	$("#ultimaCarga").html(dataCompleta);
	return ultimaCarga;

};




	function AppUi ( app ) {
		var me = this;
		this.app = app;
		// moment().locale('pt-br');
		// console.log(moment().format("DD/MM/YYYY"));			

		app.getAppLayout( function ( layout ) {
			var dataCompleta = moment(layout.qLastReloadTime).format("DD/MM/YYYY  HH:mm");
			var data = layout.qLastReloadTime.substr(0,10);
			var split = data.split('-');
			var novadata = split[2] + "-" +split[1]+"-"+split[0];
			$( "title" ).html( layout.qTitle );	
			$( "#titleApp" ).html( layout.qTitle );
			$( "#titleApp2" ).html(dataCompleta);
		} );
		$( "[data-qcmd]" ).on( 'click', function () {
			var $element = $( this );
			switch ( $element.data( 'qcmd' ) ) {
				//app level commands
				case 'clearAll':
					app.clearAll();
					break;
			}
		} );
	}

	$('a[data-toggle="tab"]').on('shown.bs.tab', function (e) {
  		qlik.resize();
	});

	//callbacks -- inserted here --	

	function toogle(){
		$("#menu-toggle").click(function(e) {
			e.preventDefault();
			$("#content").toggleClass("menu-ativo");
		});
		$("#filtro-toggle").click(function(e) {
			e.preventDefault();
			$("#content").toggleClass("filtro-ativo");
		});

		$("#btn-filtro").click(function(e) {
		$(".navegacao-direita").toggleClass("filtro-ativo");
		$(this).toggleClass('btn-fechar');		
		$('.fa-sliders-h').toggleClass('fa-times');
	});

	}toogle();

	function active(){
		$(document).ready(function() { 
			$(".menu-link").click(function (e) {
				e.preventDefault();
				$(".menu-link.active").removeClass("active");
				$(this).addClass("active"); 
			});
		});
	}active();

	$(".btnFullscreen").on("click",function(){
    	fullscreen($(this).parents(".fullscreen"));    
    	return false;
	});

	function fullscreen(panel){ 
		if (panel.hasClass("fullscreened")) {
			panel.removeClass("fullscreened");
			panel.find(".header-fullscreen a.btnFullscreen .fa").removeClass("fa-compress").addClass("fa-expand");
			qlik.resize(); 
		} else {
			panel.addClass("fullscreened");		
			panel.find(".header-fullscreen a.btnFullscreen .fa").removeClass("fa-expand").addClass("fa-compress");
			qlik.resize();
		}
	}
	

	//Função tem seleção
	function hasSelections(selections) {
		if(selections.length > 0) {
			//console.log("Tem seleção");
			return true;
		} else {
			//console.log("Não tem seleção");
			return false;
		}
	}

	//Variaveis que buscam os objetos no HTML
	var selectionsElement = document.querySelector('#selections'); 
	var buttonCurrentSelections = document.querySelectorAll('.btn-selections');

	function ocultaSelecaoAtual() {
		if(!selectionsElement.classList.contains('is-invisible')) {
			selectionsElement.classList.add('is-invisible');
		}
	}

	function setCurrentSelections(selections) {
		app.getList("CurrentSelections",function(reply){
			
			var selections = reply.qSelectionObject.qSelections;
			var html = "";

		 console.log(reply);			


			for(var i = 0; i < selections.length; i++) {
				var currentSelection = selections[i];
				var field = currentSelection.qField;
				var teste = currentSelection.qReadableName;
				var numSelected = currentSelection.qSelectedCount; 
				var total = currentSelection.qTotal;
				var threshold = currentSelection.qSelectionThreshold;
				var selectedStr = currentSelection.qSelected;

				$( "#titleApp5" ).html(selectedStr);

				selectionsElement.innerHTML = html;

				if (numSelected <= threshold) {
					html += "<li class='selected-field-container' id='" + field + "'>";
					html += "<span class='selected-field-label'>"+field+"</span>";
					html += "<div class='selected-field-value'><span class='field-value'>";
					html +=   selectedStr;
					html += "</span><i class='fas fa-trash-alt'></i></div></li>";
				}
				else {
					html += "<li class='selected-field-container' id='" + field + "'>";
					html += "<span class='selected-field-label'>"+field+"</span>";
					html += "<div class='selected-field-value'><span class='field-value'>";
					html +=   numSelected + " de " + total;
					html += "</span><i class='fas fa-trash-alt'></i></div></li>";
				} 
			}

			selectionsElement.innerHTML = html;

			$(".fa-trash-alt").click(function(evt) {
				var field = $(this).parent().parent().attr("id");
				app.field(field).clear();
				evt.stopPropagation();

				if(selections.length == 1) {
					ocultaSelecaoAtual();
				}
			});


			if(hasSelections(selections)) {
				ativaSelecoesBotao();
			} else {
				desativaSelecoesBotao();
				ocultaSelecaoAtual();
			}
			var counterElement = document.querySelector('.cd-button .counter');
			for(var i = 0; i < buttonCurrentSelections.length; i++) {
				buttonCurrentSelections[i].querySelector('.counter').innerHTML = selections.length;
			}
		});
	}

	function ativaSelecoesBotao() {
		for(var i = 1; i < buttonCurrentSelections.length; i++) {
			buttonCurrentSelections[i].removeAttribute("disabled", '');
		}
	}

	function desativaSelecoesBotao() {
		for(var i = 0; i < buttonCurrentSelections.length; i++) {
			buttonCurrentSelections[i].setAttribute("disabled", '');
		}
	}

	function mostraSelecaoAtual() {
		if(selectionsElement.classList.contains('is-invisible')) {
			selectionsElement.classList.remove('is-invisible').setAttribute('disabled', '');
		} else {
			selectionsElement.classList.add('is-invisible').setAttribute('disabled', '');
		}

	}

	$('.btn-selections').on('click', function(evt) {
		mostraSelecaoAtual();
		evt.stopPropagation();
	});

	//Conectar APP
	// console.log('Opening app...');	
	app = qlik.openApp(appID, config);
	
	if(app) {
		app.getList("CurrentSelections",function(reply){
			var selections = reply.qSelectionObject.qSelections;
			setCurrentSelections(selections);
		});
	}
	
	// app.getObject('CurrentSelections','CurrentSelections');
	

	// app.getObject('QVDASHBOARD-KPI01','JwTxe');
	// app.getObject('QVDASHBOARD-KPI02','UJnFZ');
	// app.getObject('QVDASHBOARD-KPI03','ufkBM');
	// app.getObject('QVDASHBOARD-KPI04','EKeCnR');

	//app.getObject('QVDASHBOARD-04','CWpswn');
		  	app.getObject('Tabela-1','JDnEtp');
			app.getObject('Tabela-2','fXMujgw');
			app.getObject('Tabela-3','VpyShME');
			app.getObject('Tabela-4','VeewZ');

			// app.getObject('QVFILTROS-01','QDPVpqr');
			// app.getObject('QVFILTROS-02','gyEJEAH');
			app.getObject('QVFILTROS-03','jGFCY');
			app.getObject('QVFILTROS-04','kqYr');
			app.getObject('QVFILTROS-05','RjhVp');
			app.getObject('QVFILTROS-06','gyEJEAH');
			app.getObject('QVFILTROS-07','UJPWbUH');

			// app.getObject('QVFILTROS-06','QDPVpqr');
			// app.getObject('QVFILTROS-07','gyEJEAH');
			app.getObject('QVFILTROS-08','jGFCY');
			app.getObject('QVFILTROS-09','kqYr');
			app.getObject('QVFILTROS-10','RjhVp');
			app.getObject('QVFILTROS-11','gyEJEAH');
			app.getObject('QVFILTROS-12','UJPWbUH');


$("#btn-filtro").on("click",function(e){
			app.getObject('QVFILTROS-06','QDPVpqr');
			app.getObject('QVFILTROS-07','gyEJEAH');
			app.getObject('QVFILTROS-08','jGFCY');
			app.getObject('QVFILTROS-09','kqYr');
			app.getObject('QVFILTROS-10','RjhVp');
	});



	$(".menu-link").on("click",function(e){
		var expr = (e.currentTarget.hash);
		switch (expr) {
		  case "#page1":
		  	app.getObject('Tabela-1','JDnEtp');
			app.getObject('Tabela-2','fXMujgw');
			app.getObject('Tabela-3','VpyShME');
			app.getObject('Tabela-4','VeewZ');
		    break;
		  case "#page2":
		  	app.getObject('Tabela-5','SmEzj');
			app.getObject('Tabela-6','GKjkaU');
			app.getObject('Tabela-7','MXWS');
			app.getObject('Tabela-8','kqYr');
		    break;
		  case "#page3":
		  	app.getObject('Tabela-9','vBfzHk');
		    break;
		  case "#page4":
			app.getObject('Tabela-10','phprpS');
		    break;
		}

app.visualization.get('vBfzHk').then(function (vis) {
            // mostrar o botÃ£o
            $('#GERAR_01').show();
            // mostrar o objeto.
            vis.show("QV01");
            // trigger click
            $('#GERAR_01').on('click', function () {
                $('#GERAR_01').html('Gerando arquivo');
                vis.exportData({ format: 'OOXML', state: 'A', download: true }).then(function (urlFile) {
                    window.open(urlFile);
                    $('#GERAR_01').html('Gerar arquivo');
                });
            });
        });
	});


	if ( app ) {
		new AppUi( app );
	}
	
} );