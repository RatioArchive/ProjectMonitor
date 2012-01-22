var toto = new Toto('service');

function generateStatusRow(project, admin) {

  var row = ['<tr class="project">'];

  row.push('<td class="status-box">');
  function statusBlock(code, title, message) {
    row.push('<div class="status status-');
    row.push(code);
    row.push('">');
    if(title) {
      row.push('<div class="title">');
      row.push(title);
      row.push('</div>');
    }
    if(message) {
      row.push('<div class="message">');
      row.push(message);
      row.push('</div>');
    }
    row.push('</div>');
  };

  if(admin) {
    for(var k in project.status.components) {
      statusBlock(project.status.components[k].code, k, project.status.components[k].message);
    }
  } else {
    statusBlock(project.status.code);
  }
  row.push('</td>');

  row.push('<td class="client">');
  row.push(project.client);
  row.push('</td><td class="name">');
  row.push(project.name);
  row.push('</td>');

  if(admin) {
    row.push('<td><button class="update" name="');
    row.push(project.name);
    row.push('">Update</button>');
    row.push('<button class="hide" name="');
    row.push(project.name);
    row.push('">Hide</button></td>');
  }
  row.push('</tr>');
  return row.join('');
};

function reloadStatus(admin) {
  toto.request("project.view", {}, function(response) {
    response.sort(function(a, b) {
      if(a.client == b.client) {
        var an = a.name.toLowerCase(), bn = b.name.toLowerCase();
        return ((an < bn) ? -1 : ((bn > an) ? 1 : 0))
      }
      return a.client.toLowerCase() < b.client.toLowerCase() ? -1 : 1;
    });
    $("#main").children().remove();
    window.projects = {};
    for(var i = 0; i < response.length; i++) {
      window.projects[response[i].name] = response[i];
      $("#main").append(generateStatusRow(response[i], admin));
    }
    if(admin) {
      configureAdminOptions();
    }
  }, function(error) {
    console.log(error);
  });
};

function pollServer(callback, continuous) {
    var response = function(m) {
      callback();
      if (continuous) {
          pollServer(callback, continuous);
      }  
    };
    toto.request("project.poll", {}, response, response);
}

function configureAddProjectDialog() {
  $('#add-project-dialog').dialog({
    autoOpen : false,
    height : 300,
    width : 350,
    modal : true,
    buttons : {
      "Create project" : function() {
        var valid = true;
        valid = $("#project-name").val().length > 0 && $("#project-client").val().length > 0;
        if(valid) {

          var dialog = $(this);
          toto.request("project.add", {
            "name" : $("#project-name").val(),
            "client" : $("#project-client").val()
          }, function(resp) {
            dialog.dialog("close");
            console.log(resp);
            reloadStatus(true);
          }, function(err) {
            alert(err.value);
          });
        }
      },
      Cancel : function() {
        $(this).dialog("close");
      }
    },
    close : function() {
    }
  });
};

function configureUpdateProjectDialog() {

  $('#update-project-dialog').dialog({
    autoOpen : false,
    height : 450,
    width : 300,
    modal : true,
    buttons : {
      "Update" : function() {
        var valid = true;
        valid = $("#hours_spent").val().length > 0 && $("#hours_budgeted").val().length > 0 && $("#story_progress").val().length > 0 && $("#project_progress").val().length > 0;
        if(valid) {
          var dialog = $(this);
          toto.request("project.update", {
            "hours_spent" : parseFloat($("#hours_spent").val()),
            "hours_budgeted" : parseFloat($("#hours_budgeted").val()),
            "story_progress" : parseFloat($("#story_progress").val()),
            "project_progress" : parseFloat($("#project_progress").val()),
            "name" : $(this).dialog("option", "title")
          }, function(resp) {
            dialog.dialog("close");
            console.log(resp);
            reloadStatus(true);
          }, function(err) {
            alert(err.value);
          });
        }
      },
      Cancel : function() {
        $(this).dialog("close");
      }
    },
    close : function() {
    }
  });
};

function configureAdminOptions() {
  $("#add-project").button().click(function() {
    $("#add-project-dialog").dialog("open");
  });
  $(".hide").button().click(function() {
    toto.request("project.hide", {
      "name" : $(this).attr("name")
    }, function() {
      reloadStatus(true);
    }, function() {
      reloadStatus(true);
    });
  });
  $(".update").button().click(function() {
    var project = window.projects[$(this).attr("name")];
    $("#update-project-dialog").dialog("option", "title", project["name"]);
    $("#hours_spent").val(project["hours_spent"]);
    $("#hours_budgeted").val(project["hours_budgeted"]);
    $("#story_progress").val(project["story_progress"] * 100);
    $("#project_progress").val(project["project_progress"] * 100);
    $("#update-project-dialog").dialog("open");
  });
};