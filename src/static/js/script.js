$('#myModal').on('shown.bs.modal', function () {
	$('#myInput').focus()
})


close = document.getElementById("close");
close.addEventListener('click', function() {
	commu = document.getElementById("note");
	commu.style.display = 'none';
 }, false);
	
// Forbidding the use of "|" and "£" to avoid messing up the database as these characters are used as separators
function valid(f) {
	!(/^[^|£]$/).test(f.value)?f.value = f.value.replace(/[|£]/,''):null;
}
		
function validNumber(f) {
	!(/^[\d\.]$/).test(f.value)?f.value = f.value.replace(/[^\d\.]/,''):null;
}

// Iterate through JSON to match rules numbers with rules titles
window.json = function(){
	var returnVal;

	$.ajax({
		dataType: "json",
		url: "/json",
		async: true,
		success: function(data) {
			returnVal = data;
		}
    });
    return returnVal;
}();
	
function describe(acc, box, nrdisplayed = true) {
	console.log("describe("+acc+","+box+","+nrdisplayed+")");
	var htmlText = "";
			
	if (Object.prototype.toString.call(acc) == '[object Array]') {
		for (var i = 0; i < acc.length; i++) {
			console.log("acc["+i+"] = "+acc[i]);
			htmlToAdd = describeThroughJSONArray(window.json, acc[i], nrdisplayed, htmlText);
			htmlText += htmlToAdd;
			if (i+1 < acc.length) {htmlText += "<br>"}
		}
	}
	else {
		htmlToAdd = describeThroughJSONArray(window.json, acc, nrdisplayed);
		htmlText = htmlToAdd;
	}
	
	document.getElementById(box).innerHTML = htmlText;
};
		
function describeThroughJSONArray(json, acc, nrdisplayed) {
	var htmltoAdd = "";
	
	return findAccs(json);
	
	function findAccs(json) {
		htmlToAdd = "";
		sortJsonArrayByProperty(json, 'nr');
		jsonLength = Object.keys(json).length;
		
		for (var j = 0; j < jsonLength; j++) {
			var obj = json[j];
			if (obj.nr == acc) {
				if (nrdisplayed == false) {htmlToAdd = obj.nr};
				htmlToAdd += "&nbsp;&nbsp;&nbsp;" + obj.titre;
   				console.log("ARRAY nr = " + obj.nr + " - titre = " + obj.titre);
				console.log("htmlToAdd : " + htmlToAdd);
   				break;
			}
		}
		return htmlToAdd;
	};
};

function sortJsonArrayByProperty(objArray, prop, direction){
	if (arguments.length<2) throw new Error("sortJsonArrayByProp requires 2 arguments");
	var direct = arguments.length>2 ? arguments[2] : 1; //Default to ascending

		if (objArray && objArray.constructor===Array){
		var propPath = (prop.constructor===Array) ? prop : prop.split(".");
		objArray.sort(function(a,b){
    		for (var p in propPath){
        		if (a[propPath[p]] && b[propPath[p]]){
            		a = a[propPath[p]];
            		b = b[propPath[p]];
        		}
    		}
    // convert numeric strings to integers
    		a = a.match(/^\d+$/) ? +a : a;
    		b = b.match(/^\d+$/) ? +b : b;
    		return ( (a < b) ? -1*direct : ((a > b) ? 1*direct : 0) );
		});
	}
}