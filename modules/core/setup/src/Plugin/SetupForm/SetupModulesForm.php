<?php

declare(strict_types=1);

namespace Drupal\farm_setup\Plugin\SetupForm;

use Drupal\Core\Access\AccessResult;
use Drupal\Core\Extension\ModuleExtensionList;
use Drupal\Core\Extension\ModuleHandlerInterface;
use Drupal\Core\Form\FormStateInterface;
use Drupal\Core\Session\AccountInterface;
use Drupal\Core\StringTranslation\TranslatableMarkup;
use Drupal\Core\Url;
use Drupal\farm_setup\Attribute\SetupForm;
use Drupal\farm_setup\Form\FarmModulesForm;
use Drupal\farm_setup\Form\FarmSetupBlockForm;
use Psr\Container\ContainerInterface;

/**
 * Module installation setup form.
 */
#[SetupForm(
  id: 'modules',
  title: new TranslatableMarkup('What are your record keeping needs?'),
  task_title: new TranslatableMarkup('Install modules'),
  description: new TranslatableMarkup('farmOS allows you to choose which features are relevant to your operation. These are packaged into "modules" that can be turned on/off. The questions below will help to determine what you need.'),
  weight: -95,
)]
class SetupModulesForm extends SetupFormBase {

  public function __construct(
    array $configuration,
    $plugin_id,
    $plugin_definition,
    protected ModuleHandlerInterface $moduleHandler,
    protected ModuleExtensionList $moduleExtensionList,
  ) {
    parent::__construct($configuration, $plugin_id, $plugin_definition);
  }

  /**
   * {@inheritdoc}
   */
  public static function create(ContainerInterface $container, array $configuration, $plugin_id, $plugin_definition) {
    return new static(
      $configuration,
      $plugin_id,
      $plugin_definition,
      $container->get('module_handler'),
      $container->get('extension.list.module'),
    );
  }

  /**
   * {@inheritdoc}
   */
  public function access(AccountInterface $account) {
    return AccessResult::allowedIfHasPermission($account, 'install farm modules');
  }

  /**
   * {@inheritdoc}
   */
  public function getDescription() {
    return $this->t('farmOS allows you to choose which features are relevant to your operation. These are packaged into "modules" that can be turned on/off. The questions below will help to determine what you need. Modules can also be installed individually via the <a href=":module-form-uri">farmOS modules form</a>.', [':module-form-uri' => Url::fromRoute('farm.setup.modules')->toString()])->render();
  }

  /**
   * {@inheritdoc}
   */
  public function buildForm(array $form, FormStateInterface $form_state) {
    $modules = [];

    // Operation questions.
    $operation_questions = [
      'plant' => [
        'title' => $this->t('Do you work with plants?'),
        'description' => $this->t('Installs the plant asset type.'),
        'modules' => [
          'farm_plant',
        ],
        'questions' => [
          'seeding' => [
            'title' => $this->t('Do you grow plants from seed?'),
            'description' => $this->t('Installs the seeding log type and a quick form for recording plantings.'),
            'modules' => [
              'farm_seeding',
              'farm_quick_planting',
            ],
          ],
          'transplanting' => [
            'title' => $this->t('Do you transplant?'),
            'description' => $this->t('Installs the transplanting log type and a quick form for recording plantings.'),
            'modules' => [
              'farm_transplanting',
              'farm_quick_planting',
            ],
          ],
        ],
      ],
      'animal' => [
        'title' => $this->t('Do you work with animals?'),
        'description' => $this->t('Installs the animal asset type.'),
        'modules' => [
          'farm_animal',
        ],
        'questions' => [
          'birth' => [
            'title' => $this->t('Do you track animal births?'),
            'description' => $this->t('Installs the birth log type and a quick form for recording births.'),
            'modules' => [
              'farm_birth',
              'farm_quick_birth',
            ],
          ],
          'medical' => [
            'title' => $this->t('Do you track animal medical records?'),
            'description' => $this->t('Installs the medical log type.'),
            'modules' => [
              'farm_medical',
            ],
          ],
          'movement' => [
            'title' => $this->t('Do you track animal movements?'),
            'description' => $this->t('Installs the activity log type and a quick form for recording movements.'),
            'modules' => [
              'farm_activity',
              'farm_quick_movement',
            ],
          ],
          'group' => [
            'title' => $this->t('Do you track some animals individually, and group them into herds/flocks/etc?'),
            'description' => $this->t('Installs the group asset type and a quick form for recording group assignment.'),
            'modules' => [
              'farm_group',
              'farm_observation',
              'farm_quick_group',
            ],
          ],
          'inventory' => [
            'title' => $this->t('Do you track some animals together as a single head-count, instead of as individual animals (eg: a flock of birds)?'),
            'description' => $this->t('Installs a quick form for recording inventory adjustments.'),
            'modules' => [
              'farm_observation',
              'farm_quick_inventory',
            ],
          ],
        ],
      ],
      'equipment' => [
        'title' => $this->t('Do you keep equipment records?'),
        'description' => $this->t('Installs the equipment asset type.'),
        'modules' => [
          'farm_equipment',
        ],
        'questions' => [
          'maintenance' => [
            'title' => $this->t('Do you track equipment maintenance?'),
            'description' => $this->t('Installs the maintenance log type.'),
            'modules' => [
              'farm_maintenance',
            ],
          ],
          'movement' => [
            'title' => $this->t('Do you track equipment location?'),
            'description' => $this->t('Installs the activity log type and a quick form for recording movements.'),
            'modules' => [
              'farm_activity',
              'farm_quick_movement',
            ],
          ],
        ],
      ],
      'compost' => [
        'title' => $this->t('Do you work with compost?'),
        'description' => $this->t('Installs the compost asset type.'),
        'modules' => [
          'farm_compost',
        ],
      ],
      'inventory' => [
        'title' => $this->t('Do you track inventory?'),
        'description' => $this->t('Installs a quick form for recording inventory adjustments.'),
        'modules' => [
          'farm_observation',
          'farm_quick_inventory',
        ],
        'questions' => [
          'material' => [
            'title' => $this->t('Do you track inventory of materials?'),
            'description' => $this->t('Installs the material asset type.'),
            'modules' => [
              'farm_material',
            ],
          ],
          'product' => [
            'title' => $this->t('Do you track inventory of products?'),
            'description' => $this->t('Installs the product asset type.'),
            'modules' => [
              'farm_product',
            ],
          ],
          'seed' => [
            'title' => $this->t('Do you track inventory of seed?'),
            'description' => $this->t('Installs the seed asset type.'),
            'modules' => [
              'farm_seed',
            ],
          ],
        ],
      ],
    ];
    $form['operation'] = [
      '#type' => 'fieldset',
      '#title' => $this->t('What do you do?'),
    ];
    $form['operation'] += $this->buildQuestionsForm($operation_questions);
    $modules = array_merge($modules, $this->buildModules($operation_questions, $form_state));

    // Location questions.
    $location_questions = [
      'land' => [
        'title' => $this->t('Land (eg: fields, paddocks, etc)?'),
        'description' => $this->t('Installs the land asset type and default land types.'),
        'modules' => [
          'farm_land',
          'farm_land_types',
        ],
        'questions' => [
          'lab_test' => [
            'title' => $this->t('Do you track soil lab test results?'),
            'description' => $this->t('Installs the lab test log type.'),
            'modules' => [
              'farm_lab_test',
            ],
          ],
        ],
      ],
      'structure' => [
        'title' => $this->t('Structures (buildings, greenhouses, etc.)'),
        'description' => $this->t('Installs the structure asset type and default structure types.'),
        'modules' => [
          'farm_structure',
          'farm_structure_types',
        ],
      ],
      'water' => [
        'title' => $this->t('Water (wells, ponds, etc.)'),
        'description' => $this->t('Installs the water asset type.'),
        'modules' => [
          'farm_water',
        ],
        'questions' => [
          'lab_test' => [
            'title' => $this->t('Do you track water lab test results?'),
            'description' => $this->t('Installs the lab test log type.'),
            'modules' => [
              'farm_lab_test',
            ],
          ],
        ],
      ],
    ];
    $form['locations'] = [
      '#type' => 'fieldset',
      '#title' => $this->t('Where do you do it?'),
      '#description' => $this->t('Land, structure, and water assets are used to represent locations that other records can reference.'),
    ];
    $form['locations'] += $this->buildQuestionsForm($location_questions);
    $modules = array_merge($modules, $this->buildModules($location_questions, $form_state));

    // Basic log types.
    $log_questions = [
      'activity' => [
        'title' => $this->t('General activities'),
        'description' => $this->t('Installs the activity log type.'),
        'modules' => [
          'farm_activity',
        ],
      ],
      'observation' => [
        'title' => $this->t('General observations'),
        'description' => $this->t('Installs the observation log type.'),
        'modules' => [
          'farm_observation',
        ],
      ],
      'input' => [
        'title' => $this->t('Inputs'),
        'description' => $this->t('Installs the input log type.'),
        'modules' => [
          'farm_input',
        ],
      ],
      'harvest' => [
        'title' => $this->t('Harvests'),
        'description' => $this->t('Installs the harvest log type.'),
        'modules' => [
          'farm_harvest',
        ],
      ],
    ];
    $form['logs'] = [
      '#type' => 'fieldset',
      '#title' => $this->t('What events do you record?'),
      '#description' => $this->t('Events are recorded as logs that reference locations or other assets.'),
    ];
    $form['logs'] += $this->buildQuestionsForm($log_questions);
    $modules = array_merge($modules, $this->buildModules($log_questions, $form_state));

    // Filter out duplicates.
    $modules = array_unique($modules);

    // If any log modules are installed, add the standard quantity type module.
    // We do this to ensure that at least one quantity type is available, since
    // log type modules do not explicitly depend on any specific type.
    $log_modules = array_keys(array_filter($this->moduleExtensionList->getAllAvailableInfo(), function ($module_info) {
      return isset($module_info['package']) && $module_info['package'] == 'farmOS Logs';
    }));
    if (!empty(array_intersect($modules, $log_modules))) {
      $modules[] = 'farm_quantity_standard';
    }

    // Sort modules alphabetically.
    sort($modules);

    // Build a summary of modules that will be installed.
    // This will be replaced by Ajax as the user makes selections.
    // Include all modules in the value that gets passed to form state, but
    // filter out modules that are already installed for the summary.
    $form['summary'] = [
      '#type' => 'container',
      '#attributes' => [
        'id' => 'module-summary',
      ],
    ];
    $form['summary']['modules'] = [
      '#type' => 'value',
      '#value' => $modules,
    ];
    $install_modules = array_map(function ($module) {
      return $this->moduleExtensionList->getName($module);
    }, $this->filterModules($modules));
    if (!empty($install_modules)) {
      $form['summary']['summary'] = [
        '#type' => 'fieldset',
        '#description' => $this->t('The following modules will be installed: %modules', ['%modules' => implode(', ', $install_modules)]),
      ];
    }

    // Recommend that at least one location asset type and one basic log type
    // modules are installed, but allow the user to ignore this recommendation.
    $recommended_modules = [
      'asset' => [
        'farm_land',
        'farm_structure',
        'farm_water',
      ],
      'log' => [
        'farm_activity',
        'farm_harvest',
        'farm_input',
        'farm_observation',
      ],
    ];
    if (
      empty(array_intersect($recommended_modules['asset'], $modules))
      ||
      empty(array_intersect($recommended_modules['log'], $modules))
    ) {
      $form['summary']['recommended'] = [
        '#theme' => 'status_messages',
        '#message_list' => [
          'warning' => [
            $this->t('It is recommended that at least one location asset type and one basic log type is installed. To proceed anyway, use the "Ignore recommendations" checkbox below.'),
          ],
        ],
        '#status_headings' => [
          'warning' => $this->t('Recommendations'),
        ],
      ];
      $form['summary']['ignore_recommended'] = [
        '#type' => 'checkbox',
        '#title' => $this->t('Ignore recommendations'),
        '#description' => $this->t('This allows you to proceed without installing any recommended modules.'),
        '#default_value' => FALSE,
        '#required' => TRUE,
      ];
    }

    return $form;
  }

  /**
   * Recursively build form elements from a nested array of questions.
   *
   * @param array $questions
   *   An array of question and module information.
   * @param array $parents
   *   An array of parent keys, if this is a nested question set.
   *
   * @return array
   *   Returns a form build array.
   */
  protected function buildQuestionsForm(array $questions, array $parents = []) {
    $form = [];
    foreach ($questions as $key => $info) {
      $key = implode('_', array_merge($parents, [$key]));
      $form[$key] = [
        '#type' => 'checkbox',
        '#title' => $info['title'],
        '#ajax' => [
          'callback' => [$this, 'summaryCallback'],
          'wrapper' => 'module-summary',
        ],
      ];
      if (!empty($info['modules'])) {
        $form[$key]['#default_value'] = array_reduce($info['modules'], function ($carry, $module) {
          if (!$carry) {
            return FALSE;
          }
          return $this->moduleHandler->moduleExists($module);
        }, TRUE);
        $form[$key]['#disabled'] = $form[$key]['#default_value'];
      }
      if (!empty($info['description'])) {
        $form[$key]['#description'] = $info['description'];
      }
      foreach ($parents as $parent) {
        $form[$key]['#states']['visible'] = [':input[name="' . $parent . '"]' => ['checked' => TRUE]];
      }
      if (!empty($info['questions'])) {
        $form[$key . '_questions'] = [
          '#type' => 'fieldset',
        ];
        $form[$key . '_questions'] += $this->buildQuestionsForm($info['questions'], array_merge($parents, [$key]));
        $form[$key . '_questions']['#states']['visible'] = [':input[name="' . $key . '"]' => ['checked' => TRUE]];
      }
    }
    return $form;
  }

  /**
   * Recursively build a list of modules from a questions list and form state.
   *
   * @param array $questions
   *   An array of question and module information.
   * @param \Drupal\Core\Form\FormStateInterface $form_state
   *   The form state object.
   * @param array $parents
   *   An array of parent keys, if this is a nested question set.
   *
   * @return array
   *   Returns a form build array.
   */
  protected function buildModules(array $questions, FormStateInterface $form_state, array $parents = []) {
    $modules = [];
    foreach ($questions as $key => $info) {
      $key = implode('_', array_merge($parents, [$key]));
      if (!empty($info['modules'])) {
        $selected = !empty($form_state->getValue($key));
        $modules = array_merge($modules, array_filter($info['modules'], function ($module) use ($selected) {
          return $selected || $this->moduleHandler->moduleExists($module);
        }));
      }
      if (!empty($info['questions'])) {
        $modules = array_merge($modules, $this->buildModules($info['questions'], $form_state, array_merge($parents, [$key])));
      }
    }
    return $modules;
  }

  /**
   * Filters a list of modules to only include ones that are not installed.
   *
   * @param array $modules
   *   A list of modules.
   *
   * @return array
   *   Returns the filtered list of modules.
   */
  protected function filterModules(array $modules) {
    return array_filter($modules, function ($module) {
      return !$this->moduleHandler->moduleExists($module);
    });
  }

  /**
   * Ajax callback for the modules summary.
   */
  public function summaryCallback(array $form, FormStateInterface $form_state) {
    return $form['summary'];
  }

  /**
   * {@inheritdoc}
   */
  public function submitForm(array &$form, FormStateInterface $form_state) {

    // Get list of modules to install from form state and filter out ones that
    // are already installed.
    $to_install = $this->filterModules($form_state->getValue('modules'));

    // Bail if no modules need to be installed.
    if (empty($to_install)) {
      return;
    }

    // Assemble the batch operation for installing modules.
    $operations = [];
    foreach ($to_install as $module) {
      $operations[] = [
        [FarmModulesForm::class, 'farmInstallModuleBatch'],
        [$module, $this->moduleExtensionList->getName($module)],
      ];
    }
    $batch = [
      'operations' => $operations,
      'finished' => [FarmSetupBlockForm::class, 'finishInstallModulesBatch'],
      'title' => $this->t('Installing farmOS modules'),
      'error_message' => $this->t('The installation has encountered an error.'),
    ];
    batch_set($batch);
  }

}
