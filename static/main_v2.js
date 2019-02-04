'use strict';
function begin_main(job_id = null) {
  
  console.log("Current job_id:", job_id);
  //console.log({{job_id}});
  //console.log( $("#42"), $("#42").tag );
  //$("#loading_element").toggleClass()
  //$("#42").attr("ng-show", "loading");
  //$("#42").removeAttr("id");


  angular.module('SearchToolApp', [])

  .controller('SearchToolController', ['$scope', '$log', '$http', '$timeout',
    function($scope, $log, $http, $timeout) {

    $scope.loading = false;
    $scope.urlerror = false;
    $scope.searcherror = false;
    $scope.iperror = false;
    $scope.results = null;

    $scope.testFunc = function (){
      
    };

    $scope.getResults = function() {

      // get the URL from the input
      var term = $scope.searchterm;
      var urls = $scope.searchurls;

      $scope.urlerror = false;
      $scope.searcherror = false;
      $scope.iperror = false;
      //$scope.buttonloading = true;
      //$scope.loading = true;
      $scope.results = null;

      // fire the API request
      $http.post('/search', {'searchterm': term, "searchurls" : urls}).
        success(function(job_id) {
          if(job_id == -1){
            $scope.iperror = true;
            $scope.loading = false;  
            $scope.buttonloading = true;
            //$("#submit").prop('disabled', false);
            return;
          }
          $scope.loading = true;
          $scope.buttonloading = true;

          pollJob(job_id);
        }).
        error(function(error) {
          $log.log(error);
          $scope.urlerror = true;
          $scope.loading = false;
          $scope.buttonloading = false;
        });

    };

    function pollJob(jobID, inital_delay=1000) {
      var timeout = '';

      var poller = function() {
        // fire another request
        $http.get('/results/'+jobID).
          success(function(data, status, headers, config) {
            if(status === 202) {
              $log.log(data, status);
            } else if (status === 200){
              $log.log(data);
              $scope.loading = false;
              $scope.buttonloading = false;
              $scope.results = data;
              $timeout.cancel(timeout);
              return false;
            }
            // continue to call the poller() function every 2 seconds
            // until the timeout is cancelled
            timeout = $timeout(poller, 2000);
          }).
          error(function(error) {
            $log.log("ERROR", error);
            $scope.loading = false;
            $scope.buttonloading = false;
            $scope.searcherror = true;
          });
      };

      if (inital_delay > 0){
        setTimeout(poller, inital_delay);
      }
      else{
        poller(); 
      }

    }

    if (job_id != "" && job_id != null){
      $scope.loading = true;
      $scope.buttonloading = true;
      pollJob(job_id, 0)
    };


  }]);

  setTimeout( function(){$("#submit").prop('disabled', false); }, 1);
  setTimeout( function(){$(".hidethis").removeClass("hidethis"); }, 1);
}
;
