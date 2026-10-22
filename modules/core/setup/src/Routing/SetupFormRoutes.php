<?php

declare(strict_types=1);

namespace Drupal\farm_setup\Routing;

use Drupal\Core\DependencyInjection\AutowireTrait;
use Drupal\Core\DependencyInjection\ContainerInjectionInterface;
use Drupal\farm_setup\Form\FarmSetupForm;
use Drupal\farm_setup\SetupFormPluginManager;
use Symfony\Component\DependencyInjection\Attribute\Autowire;
use Symfony\Component\Routing\Route;
use Symfony\Component\Routing\RouteCollection;

/**
 * Defines setup form routes.
 */
class SetupFormRoutes implements ContainerInjectionInterface {

  use AutowireTrait;

  public function __construct(
    #[Autowire(service: 'plugin.manager.setup_form')]
    protected SetupFormPluginManager $setupFormPluginManager,
  ) {}

  /**
   * Provides routes for setup forms.
   *
   * @return \Symfony\Component\Routing\RouteCollection
   *   Returns a route collection.
   */
  public function routes(): RouteCollection {
    $route_collection = new RouteCollection();

    // Create a /setup/wizard/[plugin_id] route for each plugin.
    // The first one will be /setup/wizard (farm.setup.wizard).
    $plugins = $this->setupFormPluginManager->getDefinitions();
    foreach ($plugins as $id => $plugin) {
      $path = '/setup/wizard';
      $route_name = 'farm.setup.wizard';
      if ($id != array_key_first($plugins)) {
        $path .= '/' . $id;
        $route_name .= '.' . $id;
      }
      $route = new Route(
        $path,
        [
          '_form' => FarmSetupForm::class,
          '_title_callback' => FarmSetupForm::class . '::getTitle',
          'plugin_id' => $id,
        ],
        [
          '_permission' => 'access farm setup wizard',
          '_custom_access' => FarmSetupForm::class . '::access',
        ],
      );
      $route_collection->add($route_name, $route);
    }

    return $route_collection;
  }

}
